"""
core — shared logic for Open Skills CLI and MCP server.

Fixes addressed:
  S1  Path traversal protection in resolve_skill/resolve_runbook
  B1  Frontmatter parser handles --- in body
  B4  Trigger matching filters stop words, requires full match
  A1  Single source of truth for scanning, state management, parsing
  A4  Atomic file writes for runbook state
  P2  Exceptions logged instead of silently swallowed
  P3  Break after first skill file match
  P4  Type hints on public API
"""

import json
import logging
import os
import re
import tempfile
import datetime
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML required: pip install pyyaml")

VERSION = "3.1.0"
SPEC_VERSION = "3.1.0"

logger = logging.getLogger("openskills")

SKELETON_SKILL = """---
name: {name}
description: Describe what this skill does.
triggers:
  - "on UI change"
boundaries:
  - "Do not run in production."
required_tools:
  - terminal
output_format: "QA_EVIDENCE.md"
disable-model-invocation: false
user-invocable: true
---

## Objective
Ensure that ...

## Procedure
1. Step one
2. Step two

## Verification Contract (NON-NEGOTIABLE)
Your job is NOT done until you provide:
- [ ] Console logs showing ...
- [ ] Screenshots in ...
"""

REQUIRED_FM_FIELDS = ["name", "description", "triggers", "boundaries", "required_tools", "output_format"]
REQUIRED_SECTIONS = ["## Objective", "## Procedure", "## Verification Contract (NON-NEGOTIABLE)"]

OPTIONAL_FM_FIELDS: dict[str, dict[str, Any]] = {
    "disable-model-invocation": {"type": bool, "default": False},
    "user-invocable": {"type": bool, "default": True},
}

PLATFORM_SPECIFIC_MARKERS = [
    ".cursorrules", "CLAUDE.md", "codex.md",
    ".cursor/rules", ".claude/skills", "AGENTS.md",
]


def slugify(name: str) -> str:
    """Slugify a skill name. Raises ValueError if result is empty."""
    safe = re.sub(r'[^a-z0-9-]', '-', name.lower().strip())
    safe = re.sub(r'-+', '-', safe).strip('-')
    if not safe:
        raise ValueError(f"Slugified name from '{name}' is empty")
    return safe


def validate_skill_content(content: str, skill_dir: Optional[Path] = None) -> dict:
    """Validate skill markdown content. Returns dict with 'errors', 'checks', and 'warnings'.

    Single source of truth for validation — used by both CLI and server.
    If skill_dir is provided, checks for adapter staleness.
    """
    fm, body = parse_frontmatter(content)
    checks = []
    errors = []
    warnings = []

    if not fm:
        errors.append("Missing or invalid YAML frontmatter block")
        checks.append({"label": "Frontmatter block exists", "passed": False})
    else:
        checks.append({"label": "Frontmatter block exists", "passed": True})

        for field in REQUIRED_FM_FIELDS:
            val = fm.get(field)
            if val is None:
                errors.append(f"Frontmatter field '{field}' is missing")
                checks.append({"label": f"Field '{field}' declared", "passed": False})
            elif field in ("triggers", "boundaries", "required_tools"):
                if not isinstance(val, list):
                    errors.append(f"Frontmatter field '{field}' must be a list")
                    checks.append({"label": f"Field '{field}' format valid", "passed": False})
                else:
                    checks.append({
                        "label": f"Field '{field}' declared",
                        "passed": True,
                        "detail": f"{len(val)} items",
                    })
            else:
                if not isinstance(val, str) or not val.strip():
                    errors.append(f"Frontmatter field '{field}' must be a non-empty string")
                    checks.append({"label": f"Field '{field}' format valid", "passed": False})
                else:
                    checks.append({
                        "label": f"Field '{field}' declared", "passed": True, "detail": val})

        for field, spec in OPTIONAL_FM_FIELDS.items():
            val = fm.get(field)
            if val is None:
                checks.append({
                    "label": f"Optional field '{field}' declared",
                    "passed": True,
                    "detail": f"default: {spec['default']}",
                })
            elif not isinstance(val, bool):
                errors.append(f"Optional field '{field}' must be a boolean (true/false)")
                checks.append({"label": f"Optional field '{field}' format valid", "passed": False})
            else:
                checks.append({
                    "label": f"Optional field '{field}' declared",
                    "passed": True,
                    "detail": str(val).lower(),
                })

    for section in REQUIRED_SECTIONS:
        if section in body:
            checks.append({"label": f"Section '{section}' exists", "passed": True})
        else:
            errors.append(f"Missing required section '{section}'")
            checks.append({"label": f"Section '{section}' exists", "passed": False})

    found_markers = [m for m in PLATFORM_SPECIFIC_MARKERS if m in body]
    if found_markers:
        errors.append(f"Body contains platform-specific syntax: {', '.join(found_markers)}")
        checks.append({"label": "Platform-agnostic body", "passed": False, "detail": ", ".join(found_markers)})
    else:
        checks.append({"label": "Platform-agnostic body", "passed": True})

    if "## Verification Contract (NON-NEGOTIABLE)" in body:
        v_section = body.split("## Verification Contract (NON-NEGOTIABLE)")[1]
        checklist = re.findall(r'- \[[ xX]\]', v_section)
        if checklist:
            checks.append({
                "label": "Verification Contract has checklist items",
                "passed": True,
                "detail": f"{len(checklist)} found",
            })
        else:
            errors.append("Verification Contract must contain at least one checklist item")
            checks.append({"label": "Verification Contract has checklist items", "passed": False})

    if skill_dir:
        adapter_dir = skill_dir / "adapters"
        if adapter_dir.is_dir():
            skill_file = find_skill_file(skill_dir)
            if skill_file:
                skill_mtime = skill_file.stat().st_mtime
                stale_adapters = []
                for af in sorted(adapter_dir.rglob("*")):
                    if af.is_file() and af.stat().st_mtime < skill_mtime:
                        stale_adapters.append(str(af.relative_to(adapter_dir)))
                if stale_adapters:
                    warnings.append(
                        f"Adapters are stale (older than skill.md): {', '.join(stale_adapters)}. "
                        "Re-run 'openskills export' to regenerate."
                    )
                    checks.append({
                        "label": "Adapters up-to-date",
                        "passed": False,
                        "detail": f"{len(stale_adapters)} stale",
                    })
                else:
                    checks.append({"label": "Adapters up-to-date", "passed": True})
            else:
                checks.append({"label": "Adapters up-to-date", "passed": True, "detail": "no skill file"})
        else:
            checks.append({"label": "Adapters up-to-date", "passed": True, "detail": "no adapters dir"})

    return {"valid": len(errors) == 0, "checks": checks, "errors": errors, "warnings": warnings}

STOP_WORDS = frozenset({
    "a", "an", "the", "on", "in", "at", "to", "for", "of", "is", "it",
    "and", "or", "do", "if", "by", "be", "as", "no", "so", "up", "not",
})

# ── Scoping & Directories ──────────────────────────────────────────────────

def get_global_dir() -> Path:
    return Path.home() / ".config" / "open-skills"


def get_local_dir() -> Path:
    curr = Path.cwd().resolve()
    for p in [curr] + list(curr.parents):
        if (p / ".open-skills").is_dir() or (p / ".git").exists():
            return p / ".open-skills"
    return curr / ".open-skills"


# ── Path Safety ─────────────────────────────────────────────────────────────

def _safe_child(base: Path, name: str) -> Path:
    """Resolve name under base, raising ValueError on traversal."""
    resolved = (base / name).resolve()
    base_resolved = base.resolve()
    if not resolved.is_relative_to(base_resolved):
        raise ValueError(f"Path traversal blocked: '{name}' escapes '{base}'")
    return resolved


# ── Resolution ──────────────────────────────────────────────────────────────

def resolve_skill(name: str) -> tuple[Optional[Path], Optional[Path]]:
    """Find a skill by name. Checks local, then global, then direct path."""
    for scope_dir in [get_local_dir(), get_global_dir()]:
        try:
            skill_dir = _safe_child(scope_dir / "skills", name)
        except ValueError:
            continue
        for fn in ["skill.md", "SKILL.md"]:
            if (skill_dir / fn).exists():
                return skill_dir, skill_dir / fn

    p = Path(name)
    if p.is_dir():
        for fn in ["skill.md", "SKILL.md"]:
            if (p / fn).exists():
                return p, p / fn

    return None, None


def resolve_runbook(name: str) -> Optional[Path]:
    """Find a runbook by name. Checks local, then global, then direct path."""
    if not name.endswith(".md"):
        name_ext = f"{name}.md"
    else:
        name_ext = name

    for scope_dir in [get_local_dir(), get_global_dir()]:
        try:
            rb = _safe_child(scope_dir / "runbooks", name_ext)
        except ValueError:
            continue
        if rb.exists():
            return rb

    p = Path(name_ext)
    if p.exists():
        return p

    return None


# ── Parsing ─────────────────────────────────────────────────────────────────

_FM_RE = re.compile(r'\A\s*---[ \t]*\n(.*?\n)---[ \t]*\n(.*)', re.DOTALL)
_FM_UNCLOSED_RE = re.compile(
    r'\A\s*---[ \t]*\n(.*?\n)(?=## )', re.DOTALL,
)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown. Returns (dict, body).

    Handles both proper ---/--- fences and unclosed frontmatter where
    the closing --- is missing (falls back to splitting at the first ## header).
    """
    m = _FM_RE.match(text)
    if m:
        try:
            fm = yaml.safe_load(m.group(1))
            return fm or {}, m.group(2).strip()
        except Exception as e:
            logger.warning("Failed to parse YAML frontmatter: %s", e)

    m = _FM_UNCLOSED_RE.match(text)
    if m:
        try:
            fm = yaml.safe_load(m.group(1))
            if fm and isinstance(fm, dict):
                body = text[m.end():].strip()
                logger.warning("Parsed frontmatter with missing closing ---")
                return fm, body
        except Exception:
            pass

    return {}, text


# ── Skill Scanning ──────────────────────────────────────────────────────────

def find_skill_file(directory: Path) -> Optional[Path]:
    """Return the first skill markdown file in directory, or None."""
    for fn in ["skill.md", "SKILL.md"]:
        fp = directory / fn
        if fp.exists():
            return fp
    return None


def scan_skills(scope_dir: Path, scope_name: str) -> list[dict[str, Any]]:
    """Scan a scope directory for skills and return metadata dicts."""
    skills: list[dict[str, Any]] = []
    skills_dir = scope_dir / "skills"
    if not skills_dir.is_dir():
        return skills
    for item in sorted(skills_dir.iterdir()):
        if not item.is_dir():
            continue
        fp = find_skill_file(item)
        if not fp:
            continue
        try:
            content = fp.read_text()
            fm, body = parse_frontmatter(content)
            skills.append({
                "name": fm.get("name", item.name),
                "scope": scope_name,
                "path": fp,
                "description": fm.get("description", ""),
                "triggers": fm.get("triggers", []),
                "boundaries": fm.get("boundaries", []),
                "required_tools": fm.get("required_tools", []),
                "output_format": fm.get("output_format", ""),
                "disable_model_invocation": fm.get("disable-model-invocation", False),
                "user_invocable": fm.get("user-invocable", True),
                "body": body,
            })
        except Exception as e:
            logger.warning("Failed to load skill from %s: %s", fp, e)
    return skills


def get_all_skills() -> tuple[list[dict[str, Any]], list[str]]:
    """Return (merged skills list, shadowed names). Local overrides global."""
    global_skills = scan_skills(get_global_dir(), "Global")
    local_skills = scan_skills(get_local_dir(), "Local")

    by_name: dict[str, dict[str, Any]] = {}
    shadowed: list[str] = []
    for s in global_skills:
        by_name[s["name"]] = s
    for s in local_skills:
        if s["name"] in by_name:
            shadowed.append(s["name"])
        by_name[s["name"]] = s

    return list(by_name.values()), shadowed


# ── Runbook Parsing ─────────────────────────────────────────────────────────

def parse_runbook(filepath: Path) -> list[dict[str, str]]:
    """Parse a runbook markdown table into phase dicts."""
    lines = filepath.read_text().splitlines()
    phases: list[dict[str, str]] = []

    header_found = False
    for line in lines:
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if parts and parts[0] == "":
            parts = parts[1:]
        if parts and parts[-1] == "":
            parts = parts[:-1]

        if not header_found:
            if (len(parts) >= 4
                    and "phase" in parts[0].lower()
                    and "skill" in parts[1].lower()):
                header_found = True
            continue

        if all(all(c in "-:| " for c in p) for p in parts if p):
            continue

        if len(parts) >= 4:
            if len(parts) > 4:
                logger.warning("Runbook row has %d columns, only 4 are used: %s", len(parts), line)
            phases.append({
                "phase": parts[0],
                "skill": parts[1],
                "input": parts[2],
                "output": parts[3],
                "status": "pending",
            })
    return phases


# ── Runbook State Management ────────────────────────────────────────────────

def get_runbook_state_file() -> Path:
    return get_local_dir() / ".runbook-state"


def _write_state_atomic(state_file: Path, state: dict) -> None:
    """Write state via temp file + atomic rename."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(state_file.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, str(state_file))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_runbook_state() -> Optional[dict]:
    sf = get_runbook_state_file()
    if not sf.exists():
        return None
    return json.loads(sf.read_text())


def start_runbook(name: str) -> dict:
    """Start a runbook by name. Returns result dict."""
    rb_file = resolve_runbook(name)
    if not rb_file:
        return {"status": "error", "message": f"Runbook '{name}' not found"}

    phases = parse_runbook(rb_file)
    if not phases:
        return {"status": "error", "message": f"No phases parsed from '{rb_file}'"}

    all_skills, _ = get_all_skills()
    skill_names = {s["name"] for s in all_skills}
    missing_skills = []
    for p in phases:
        if p["skill"] not in skill_names:
            missing_skills.append(p["skill"])
    warnings = []
    if missing_skills:
        warnings.append(
            f"Referenced skills not found: {', '.join(sorted(set(missing_skills)))}. "
            "These phases will fail at execution time."
        )

    state = {
        "runbook": rb_file.stem,
        "current_phase": phases[0]["phase"],
        "phases": phases,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _write_state_atomic(get_runbook_state_file(), state)
    return {
        "status": "success",
        "message": f"Started runbook '{rb_file.stem}' with {len(phases)} phases. "
                   f"Active phase: {state['current_phase']}.",
        "state": state,
        "warnings": warnings,
    }


def advance_runbook() -> dict:
    """Advance active runbook to the next phase."""
    sf = get_runbook_state_file()
    state = read_runbook_state()
    if not state:
        return {"status": "error", "message": "No active runbook"}

    curr_phase = state.get("current_phase")
    if curr_phase is None:
        return {"status": "error", "message": "Runbook already completed"}

    phases = state["phases"]
    idx = next((i for i, p in enumerate(phases) if p["phase"] == curr_phase), -1)
    if idx == -1:
        return {"status": "error", "message": f"Phase '{curr_phase}' not found"}

    phases[idx]["status"] = "completed"

    if idx + 1 < len(phases):
        state["current_phase"] = phases[idx + 1]["phase"]
        msg = f"Phase {curr_phase} completed. Advanced to Phase {state['current_phase']}: {phases[idx+1]['skill']}"
    else:
        state["current_phase"] = None
        msg = f"Phase {curr_phase} completed. Runbook '{state['runbook']}' is now fully completed!"

    state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _write_state_atomic(sf, state)
    return {"status": "success", "message": msg, "state": state}


def prev_runbook() -> dict:
    """Move active runbook back to the previous phase."""
    sf = get_runbook_state_file()
    state = read_runbook_state()
    if not state:
        return {"status": "error", "message": "No active runbook state found"}

    curr_phase = state.get("current_phase")
    phases = state["phases"]

    if curr_phase is None:
        idx = len(phases)
    else:
        idx = next((i for i, p in enumerate(phases) if p["phase"] == curr_phase), -1)

    if idx == -1:
        return {"status": "error", "message": f"Active phase '{curr_phase}' not found"}

    if idx == 0:
        return {"status": "error", "message": "Already at the first phase"}

    new_idx = idx - 1
    state["current_phase"] = phases[new_idx]["phase"]
    phases[new_idx]["status"] = "pending"
    if idx < len(phases):
        phases[idx]["status"] = "pending"

    state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _write_state_atomic(sf, state)
    return {
        "status": "success",
        "message": f"Reverted to Phase {state['current_phase']}: {phases[new_idx]['skill']}",
        "state": state,
    }


def reset_runbook() -> dict:
    """Delete the active runbook state file."""
    sf = get_runbook_state_file()
    if sf.exists():
        sf.unlink()
        return {"status": "success", "message": "Runbook state reset."}
    return {"status": "success", "message": "No active runbook to reset."}


# ── Trigger Matching ────────────────────────────────────────────────────────

def match_triggers(prompt: str, skills: Optional[list[dict]] = None) -> list[dict]:
    """Match user prompt against skill triggers. Returns matching skills.

    Skills with disable-model-invocation=true are excluded from
    automatic trigger matching — they must be explicitly invoked by the user.
    """
    if skills is None:
        skills, _ = get_all_skills()

    skills = [s for s in skills if not s.get("disable_model_invocation", False)]

    matches: list[dict] = []
    prompt_lower = prompt.lower()
    prompt_words = set(re.findall(r'\w+', prompt_lower)) - STOP_WORDS

    for s in skills:
        for t in s.get("triggers", []):
            if t.lower() in prompt_lower:
                matches.append({
                    "name": s["name"],
                    "scope": s.get("scope", "unknown"),
                    "matched_trigger": t,
                    "description": s.get("description", ""),
                    "suggested_injection": s.get("body", ""),
                })
                break
            trigger_words = set(re.findall(r'\w+', t.lower())) - STOP_WORDS
            if len(trigger_words) >= 2 and trigger_words.issubset(prompt_words):
                matches.append({
                    "name": s["name"],
                    "scope": s.get("scope", "unknown"),
                    "matched_trigger": t,
                    "description": s.get("description", ""),
                    "suggested_injection": s.get("body", ""),
                })
                break

    return matches
