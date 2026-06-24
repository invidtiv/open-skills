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
import sys
import tempfile
import datetime
import time
import platform
import shutil
import urllib.request
from pathlib import Path
from typing import Any, Optional, Callable

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML required: pip install pyyaml")

VERSION = "3.2.0"
SPEC_VERSION = "3.2.0"

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


# ── Skill Recommendation ────────────────────────────────────────────────────

RECOMMEND_MIN_CANDIDATES = 3

_RECOMMEND_SYSTEM_PROMPT = (
    "You are a skill-routing classifier for an AI agent. "
    "Given a task and a list of candidate skills (each with a name, description, and triggers), "
    "return ONLY a JSON array ranking the most relevant skills for the task. "
    'Each element: {"name": <exact skill name>, "score": <0.0–1.0 relevance>, "reason": <one short sentence>}. '
    "Return at most N items, highest score first. No prose, no markdown, no code fences."
)


def _prefilter_candidates(query: str, skills: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    """Deterministic pre-filter: trigger matching + keyword overlap on name/description.

    Returns up to `cap` candidates sorted by relevance score (descending).
    """
    query_lower = query.lower()
    query_words = set(re.findall(r'\w+', query_lower)) - STOP_WORDS

    scored: list[tuple[float, dict[str, Any]]] = []
    for s in skills:
        if s.get("disable_model_invocation", False):
            continue
        score = 0.0
        name_lower = s.get("name", "").lower()
        desc_lower = s.get("description", "").lower()

        for t in s.get("triggers", []):
            t_str = t if isinstance(t, str) else str(t)
            t_lower = t_str.lower()
            if t_lower in query_lower:
                score += 3.0
                break
            trigger_words = set(re.findall(r'\w+', t_lower)) - STOP_WORDS
            if len(trigger_words) >= 2 and trigger_words.issubset(query_words):
                score += 2.0
                break

        for w in query_words:
            if w in name_lower:
                score += 1.0
            if w in desc_lower:
                score += 0.5

        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:cap]]


def _parse_llm_ranking(raw: str, candidate_names: set[str], limit: int) -> list[dict[str, Any]]:
    """Parse LLM JSON ranking response, validate names, clamp scores."""
    text = raw.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)

    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        return []

    if not isinstance(items, list):
        return []

    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name or name not in candidate_names:
            continue
        score = item.get("score", 0.0)
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(1.0, score))
        reason = str(item.get("reason", ""))[:140]
        results.append({"name": name, "score": score, "reason": reason})
        if len(results) >= limit:
            break

    return results


def recommend_skills(
    query: str,
    *,
    scope: str = "all",
    limit: int = 5,
    candidate_cap: int = 20,
    llm_call: Optional[Callable[[str, str], str]] = None,
) -> dict:
    """Rank skills by relevance to `query`.

    Pipeline:
      1. candidates = prefilter(query, get_all_skills(scope), candidate_cap)
      2. if no API key OR llm unavailable -> return prefilter order (degraded mode, llm_used=False)
      3. ranked = llm_rank(query, candidates) -> parse strict JSON
      4. return top `limit`

    Returns dict with query, llm_used, model, results, candidate_count, elapsed_ms.
    """
    start = time.monotonic()

    all_skills, _ = get_all_skills()
    if scope == "local":
        all_skills = [s for s in all_skills if s.get("scope", "").lower() == "local"]
    elif scope == "global":
        all_skills = [s for s in all_skills if s.get("scope", "").lower() == "global"]

    candidates = _prefilter_candidates(query, all_skills, candidate_cap)

    if len(candidates) < RECOMMEND_MIN_CANDIDATES:
        candidates = [s for s in all_skills if not s.get("disable_model_invocation", False)][:candidate_cap]

    candidate_names = {s["name"] for s in candidates}

    def _degraded_result() -> dict:
        results = []
        for s in candidates[:limit]:
            results.append({
                "name": s["name"],
                "scope": s.get("scope", "unknown"),
                "score": 0.0,
                "reason": "keyword match (degraded mode)",
                "triggers": s.get("triggers", []),
            })
        elapsed = int((time.monotonic() - start) * 1000)
        return {
            "query": query,
            "llm_used": False,
            "model": None,
            "results": results,
            "candidate_count": len(candidates),
            "elapsed_ms": elapsed,
        }

    if llm_call is None:
        api_key = get_api_key()

        if not api_key:
            logger.info("recommend_skills: no API key, using degraded mode")
            result = _degraded_result()
            logger.info(
                "recommend_skills: query=%r candidate_count=%d llm_used=False top=%s elapsed_ms=%d",
                query, result["candidate_count"],
                result["results"][0]["name"] if result["results"] else "none",
                result["elapsed_ms"],
            )
            return result

        model = os.environ.get("RECOMMEND_MODEL") or os.environ.get("EXTRACT_MODEL") or "deepseek/deepseek-v4-flash"
        api_base = os.environ.get("RECOMMEND_API_BASE") or os.environ.get("EXTRACT_API_BASE") or "https://openrouter.ai/api/v1/chat/completions"
        timeout_ms = int(os.environ.get("RECOMMEND_TIMEOUT_MS", "2000"))
        timeout_s = timeout_ms / 1000.0

        def _default_llm(sys_prompt: str, user_prompt: str) -> str:
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            req = urllib.request.Request(
                api_base,
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"]

        llm_call = _default_llm
    else:
        model = os.environ.get("RECOMMEND_MODEL") or os.environ.get("EXTRACT_MODEL") or "deepseek/deepseek-v4-flash"

    candidate_lines = []
    for s in candidates:
        triggers_list = s.get("triggers", [])
        triggers_str = ", ".join(t if isinstance(t, str) else str(t) for t in triggers_list) if triggers_list else "none"
        candidate_lines.append(
            f"- name: {s['name']}\n  description: {s.get('description', '')}\n  triggers: {triggers_str}"
        )
    user_prompt = (
        f"Task: {query}\n\n"
        f"Candidate skills (return at most {limit}):\n" + "\n".join(candidate_lines)
    )

    try:
        raw_response = llm_call(_RECOMMEND_SYSTEM_PROMPT, user_prompt)
        ranked = _parse_llm_ranking(raw_response, candidate_names, limit)
    except Exception as e:
        logger.warning("recommend_skills: LLM call failed: %s, using degraded mode", e)
        result = _degraded_result()
        logger.info(
            "recommend_skills: query=%r candidate_count=%d llm_used=False model=%s top=%s elapsed_ms=%d",
            query, result["candidate_count"], model,
            result["results"][0]["name"] if result["results"] else "none",
            result["elapsed_ms"],
        )
        return result

    if not ranked:
        logger.warning("recommend_skills: LLM returned no valid results, using degraded mode")
        result = _degraded_result()
        logger.info(
            "recommend_skills: query=%r candidate_count=%d llm_used=False model=%s top=%s elapsed_ms=%d",
            query, result["candidate_count"], model,
            result["results"][0]["name"] if result["results"] else "none",
            result["elapsed_ms"],
        )
        return result

    skill_map = {s["name"]: s for s in candidates}
    results = []
    for r in ranked:
        s = skill_map.get(r["name"])
        if not s:
            continue
        results.append({
            "name": r["name"],
            "scope": s.get("scope", "unknown"),
            "score": r["score"],
            "reason": r["reason"],
            "triggers": s.get("triggers", []),
        })

    elapsed = int((time.monotonic() - start) * 1000)
    result = {
        "query": query,
        "llm_used": True,
        "model": model,
        "results": results,
        "candidate_count": len(candidates),
        "elapsed_ms": elapsed,
    }
    logger.info(
        "recommend_skills: query=%r candidate_count=%d llm_used=True model=%s top=%s elapsed_ms=%d",
        query, result["candidate_count"], model,
        result["results"][0]["name"] if result["results"] else "none",
        result["elapsed_ms"],
    )
    return result


# ── LLM Config & API Key ──────────────────────────────────────────────────

EXTRACT_API_BASE = "https://openrouter.ai/api/v1/chat/completions"
EXTRACT_MODEL = "deepseek/deepseek-v4-flash"


def get_api_key() -> Optional[str]:
    """Get OpenRouter API key from environment or .env file."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key

    for env_path in [Path.cwd() / ".env", Path(__file__).parent / ".env"]:
        if env_path.exists():
            try:
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    if k.strip() == "OPENROUTER_API_KEY":
                        v = v.strip().strip("'\"")
                        if v:
                            return v
            except Exception:
                continue
    return None


# ── Skill Extraction Pipeline ──────────────────────────────────────────────

_EXTRACT_SYSTEM_PROMPT = (
    "You are an expert technical writer and AI systems engineer.\n"
    "Your task is to analyze the following chat transcript between a User and an Assistant.\n"
    "Identify any repeatable, non-obvious technical procedures used or discussed in the chat.\n"
    "Format the output strictly as an Open Skill markdown file.\n\n"
    "The output MUST follow this EXACT structure — pay special attention to the\n"
    "opening AND closing --- fences around the YAML frontmatter:\n\n"
    "---\n"
    "name: <slugified-skill-name>\n"
    "description: <concise-description>\n"
    "triggers:\n"
    "  - \"<trigger-condition-1>\"\n"
    "boundaries:\n"
    "  - \"<boundary-condition-1>\"\n"
    "required_tools:\n"
    "  - <tool-1>\n"
    "output_format: \"<expected-output-format>\"\n"
    "---\n\n"
    "## Objective\n"
    "<Description of the objective of this skill>\n\n"
    "## Procedure\n"
    "1. <Step 1>\n"
    "2. <Step 2>\n\n"
    "## Verification Contract (NON-NEGOTIABLE)\n"
    "Your job is NOT done until you provide:\n"
    "- [ ] <Checklist item 1>\n"
    "- [ ] <Checklist item 2>\n\n"
    "CRITICAL RULES:\n"
    "- The YAML block MUST start with --- on its own line AND end with --- on its own line.\n"
    "- Do NOT omit the closing --- fence. Without it the file is invalid.\n"
    "- Do not wrap the response in markdown code blocks like ```markdown.\n"
    "- Respond ONLY with the raw markdown text starting with ---."
)


def get_last_session_transcript() -> Optional[str]:
    """Read the most recent chat session transcript from Superpowers DB or Claude history."""
    db_path = Path.home() / ".config" / "superpowers" / "conversation-index" / "db.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT session_id, max(timestamp) FROM exchanges "
                    "GROUP BY session_id ORDER BY max(timestamp) DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    session_id = row[0]
                    cursor.execute(
                        "SELECT user_message, assistant_message FROM exchanges "
                        "WHERE session_id = ? ORDER BY timestamp ASC",
                        (session_id,),
                    )
                    rows = cursor.fetchall()
                    if rows:
                        transcript = []
                        for user, assistant in rows:
                            transcript.append(f"User: {user}")
                            transcript.append(f"Assistant: {assistant}")
                        return "\n\n".join(transcript)
        except Exception as e:
            logger.warning("Failed to read from Superpowers DB: %s", e)

    history_file = Path.home() / ".claude" / "history.jsonl"
    if history_file.exists():
        try:
            lines = history_file.read_text().splitlines()
            if lines:
                last_line_data = json.loads(lines[-1])
                session_id = last_line_data.get("sessionId")
                if session_id:
                    transcript = []
                    for line in lines:
                        try:
                            data = json.loads(line)
                            if data.get("sessionId") == session_id and data.get("display"):
                                transcript.append(f"User: {data['display']}")
                        except Exception:
                            continue
                    if transcript:
                        return "\n\n".join(transcript)
        except Exception as e:
            logger.warning("Failed to read from Claude history log: %s", e)

    return None


def call_llm_extraction(api_key: str, transcript: str) -> str:
    """Call OpenRouter API to extract a skill from a transcript."""
    data = {
        "model": EXTRACT_MODEL,
        "messages": [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Here is the chat transcript:\n\n{transcript}\n\nApply the instructions and extract the skill."},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(
        EXTRACT_API_BASE,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"OpenRouter API call failed: {e}")


def extract_skill_name_from_md(md_content: str) -> str:
    """Extract and slugify the skill name from markdown content."""
    fm, _ = parse_frontmatter(md_content)
    name = fm.get("name")
    if name:
        try:
            return slugify(name)
        except ValueError:
            pass
    return "extracted-skill"


# ── Agent MCP Registration ──────────────────────────────────────────────────

AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "cursor": {
        "label": "Cursor",
        "format": "mcp-json",
        "paths": {
            "darwin": "~/.cursor/mcp.json",
            "linux": "~/.cursor/mcp.json",
            "windows": "%USERPROFILE%\\.cursor\\mcp.json",
        },
        "servers_key": "mcpServers",
    },
    "claude-code": {
        "label": "Claude Code",
        "format": "mcp-json",
        "paths": {
            "darwin": "~/.mcp.json",
            "linux": "~/.mcp.json",
            "windows": "%USERPROFILE%\\.mcp.json",
        },
        "servers_key": "mcpServers",
    },
    "devin": {
        "label": "Windsurf / Devin",
        "format": "mcp-json",
        "paths": {
            "darwin": "~/.codeium/windsurf/mcp_config.json",
            "linux": "~/.codeium/windsurf/mcp_config.json",
            "windows": "%USERPROFILE%\\.codeium\\windsurf\\mcp_config.json",
        },
        "servers_key": "mcpServers",
    },
    "codex": {
        "label": "Codex",
        "format": "mcp-toml",
        "paths": {
            "darwin": "~/.codex/config.toml",
            "linux": "~/.codex/config.toml",
            "windows": "%USERPROFILE%\\.codex\\config.toml",
        },
        "servers_key": "mcp_servers",
    },
    "hermes": {
        "label": "Hermes",
        "format": "mcp-yaml",
        "paths": {
            "darwin": "~/.hermes/config.yaml",
            "linux": "~/.hermes/config.yaml",
            "windows": "%USERPROFILE%\\.hermes\\config.yaml",
        },
        "servers_key": "mcp_servers",
    },
    "kimi": {
        "label": "Kimi",
        "format": "mcp-json",
        "paths": {
            "darwin": "~/.kimi/mcp.json",
            "linux": "~/.kimi/mcp.json",
            "windows": "%USERPROFILE%\\.kimi\\mcp.json",
        },
        "servers_key": "mcpServers",
    },
}

SERVER_ENTRY_NAME = "open-skills"


def _resolve_agent_config_path(agent_id: str, system: Optional[str] = None) -> Optional[Path]:
    """Resolve the config file path for an agent on the current OS."""
    agent = AGENT_REGISTRY.get(agent_id)
    if not agent:
        return None
    sys_name = system or platform.system().lower()
    if sys_name == "darwin":
        sys_key = "darwin"
    elif sys_name.startswith("win"):
        sys_key = "windows"
    else:
        sys_key = "linux"

    raw_path = agent["paths"].get(sys_key)
    if not raw_path:
        return None

    if sys_key == "windows":
        home = os.environ.get("USERPROFILE", str(Path.home()))
        raw_path = raw_path.replace("%USERPROFILE%", home)
    else:
        raw_path = os.path.expanduser(raw_path)

    return Path(raw_path)


def _build_server_entry(scope: str = "all") -> dict:
    """Build the MCP server entry dict for the open-skills server."""
    openskills_path = Path(__file__).parent.resolve() / "openskills.py"
    return {
        "command": "python3",
        "args": [str(openskills_path), "mcp", "start", "--scope", scope],
        "env": {},
    }


def _backup_file(path: Path) -> Optional[Path]:
    """Create a timestamped backup of a file. Returns backup path or None if file doesn't exist."""
    if not path.exists():
        return None
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.parent / f"{path.name}.bak-{ts}"
    shutil.copy2(str(path), str(backup))
    return backup


def _read_mcp_json_config(path: Path) -> dict:
    """Read and parse an mcp-json config file. Returns empty dict if missing."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"Failed to parse config file {path}: {e}")


def _write_mcp_json_config(path: Path, config: dict) -> None:
    """Write config as JSON, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n")


def _read_toml_config(path: Path) -> dict:
    """Read and parse a TOML config file. Returns empty dict if missing."""
    if not path.exists():
        return {}
    try:
        import tomllib
        return tomllib.loads(path.read_text())
    except Exception as e:
        raise ValueError(f"Failed to parse TOML config {path}: {e}")


def _toml_entry_for_server(entry: dict) -> str:
    """Render a single MCP server entry as TOML text."""
    lines = [f'[mcp_servers.{SERVER_ENTRY_NAME}]']
    lines.append(f'command = {json.dumps(entry["command"])}')
    args_str = ", ".join(json.dumps(a) for a in entry["args"])
    lines.append(f"args = [ {args_str} ]")
    if entry.get("env"):
        lines.append("")
        lines.append(f"[mcp_servers.{SERVER_ENTRY_NAME}.env]")
        for k, v in entry["env"].items():
            lines.append(f'{k} = {json.dumps(v)}')
    return "\n".join(lines) + "\n"


def _remove_toml_server_section(content: str) -> str:
    """Remove the [mcp_servers.open-skills] section (and its .env sub-section) from TOML text."""
    lines = content.splitlines(keepends=True)
    result = []
    skip = False
    header_re = re.compile(r'^\[')
    target_re = re.compile(rf'^\[mcp_servers\.{re.escape(SERVER_ENTRY_NAME)}(\]|\.)')
    for line in lines:
        if target_re.match(line.strip()):
            skip = True
            continue
        if skip and header_re.match(line.strip()) and not target_re.match(line.strip()):
            skip = False
        if not skip:
            result.append(line)
    return "".join(result)


def _read_yaml_config(path: Path) -> dict:
    """Read and parse a YAML config file. Returns empty dict if missing."""
    if not path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(path.read_text()) or {}
    except Exception as e:
        raise ValueError(f"Failed to parse YAML config {path}: {e}")


def _yaml_entry_for_server(entry: dict) -> str:
    """Render a single MCP server entry as YAML text to append under mcp_servers:."""
    import yaml
    return yaml.dump(
        {"mcp_servers": {SERVER_ENTRY_NAME: entry}},
        default_flow_style=False,
        sort_keys=False,
    )


def _generate_diff(old_content: str, new_content: str) -> str:
    """Generate a simple unified diff between old and new content."""
    import difflib
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile="before", tofile="after",
    )
    return "".join(diff)


def detect_agents() -> list[dict[str, Any]]:
    """Detect all registry agents and their install status.

    Returns list of dicts: id, label, detected, installed, configPath, format.
    """
    results = []
    for agent_id, agent in AGENT_REGISTRY.items():
        config_path = _resolve_agent_config_path(agent_id)
        detected = config_path is not None and config_path.exists()
        installed = False
        if detected:
            try:
                fmt = agent["format"]
                if fmt == "mcp-toml":
                    config = _read_toml_config(config_path)
                elif fmt == "mcp-yaml":
                    config = _read_yaml_config(config_path)
                else:
                    config = _read_mcp_json_config(config_path)
                servers = config.get(agent["servers_key"], {})
                installed = SERVER_ENTRY_NAME in servers
            except Exception:
                installed = False

        results.append({
            "id": agent_id,
            "label": agent["label"],
            "detected": detected,
            "installed": installed,
            "configPath": str(config_path) if config_path else "",
            "format": agent["format"],
        })
    return results


def connect_agent(
    agent_id: str,
    *,
    scope: str = "all",
    dry_run: bool = False,
    config_path: Optional[str] = None,
    format: str = "mcp-json",
) -> dict[str, Any]:
    """Register the Open Skills MCP server into an agent's config file.

    Returns dict with action, path, diff (if dry_run).
    """
    if config_path:
        target_path = Path(config_path).expanduser()
        servers_key = "mcpServers"
        fmt = format
    else:
        agent = AGENT_REGISTRY.get(agent_id)
        if not agent:
            return {"action": "failed", "path": "", "error": f"Unknown agent: {agent_id}"}
        target_path = _resolve_agent_config_path(agent_id)
        if target_path is None:
            return {"action": "failed", "path": "", "error": f"No config path for agent '{agent_id}' on this OS"}
        servers_key = agent["servers_key"]
        fmt = agent["format"]

    if fmt not in ("mcp-json", "mcp-toml", "mcp-yaml"):
        return {"action": "failed", "path": "", "error": f"Unsupported format: {fmt}"}

    entry = _build_server_entry(scope)
    old_content = target_path.read_text() if target_path.exists() else ""

    if fmt == "mcp-toml":
        return _connect_agent_toml(target_path, old_content, entry, dry_run, agent_id)
    if fmt == "mcp-yaml":
        return _connect_agent_yaml(target_path, old_content, entry, dry_run, agent_id)

    try:
        config = json.loads(old_content) if old_content else {}
    except json.JSONDecodeError as e:
        return {"action": "failed", "path": str(target_path), "error": f"Config file is not valid JSON: {e}"}

    if not isinstance(config, dict):
        return {"action": "failed", "path": str(target_path), "error": "Config file root is not a JSON object"}

    servers = config.setdefault(servers_key, {})

    was_installed = SERVER_ENTRY_NAME in servers
    action = "updated" if was_installed else "installed"

    servers[SERVER_ENTRY_NAME] = entry

    new_content = json.dumps(config, indent=2) + "\n"
    diff = _generate_diff(old_content, new_content) if old_content else None

    if dry_run:
        return {"action": action, "path": str(target_path), "diff": diff or new_content}

    backup = _backup_file(target_path)

    _write_mcp_json_config(target_path, config)

    try:
        verify = json.loads(target_path.read_text())
        if not isinstance(verify, dict):
            raise ValueError("Verified content is not a dict")
    except Exception as e:
        if backup and backup.exists():
            shutil.copy2(str(backup), str(target_path))
        return {"action": "failed", "path": str(target_path), "error": f"Write validation failed, rolled back: {e}"}

    logger.info("connect_agent: agent=%s action=%s path=%s", agent_id, action, target_path)
    return {"action": action, "path": str(target_path), "diff": diff}


def _connect_agent_toml(
    target_path: Path, old_content: str, entry: dict, dry_run: bool, agent_id: str,
) -> dict[str, Any]:
    """Handle connect for TOML-format configs (Codex)."""
    try:
        config = _read_toml_config(target_path) if old_content else {}
    except ValueError as e:
        return {"action": "failed", "path": str(target_path), "error": str(e)}

    servers = config.get("mcp_servers", {})
    was_installed = SERVER_ENTRY_NAME in servers
    action = "updated" if was_installed else "installed"

    cleaned = _remove_toml_server_section(old_content) if old_content else ""
    section_text = _toml_entry_for_server(entry)
    new_content = cleaned.rstrip("\n") + "\n\n" + section_text if cleaned.strip() else section_text
    diff = _generate_diff(old_content, new_content) if old_content else None

    if dry_run:
        return {"action": action, "path": str(target_path), "diff": diff or new_content}

    backup = _backup_file(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(new_content)

    try:
        import tomllib
        verify = tomllib.loads(target_path.read_text())
        if not isinstance(verify, dict):
            raise ValueError("Verified content is not a dict")
    except Exception as e:
        if backup and backup.exists():
            shutil.copy2(str(backup), str(target_path))
        return {"action": "failed", "path": str(target_path), "error": f"Write validation failed, rolled back: {e}"}

    logger.info("connect_agent: agent=%s action=%s path=%s", agent_id, action, target_path)
    return {"action": action, "path": str(target_path), "diff": diff}


def _remove_yaml_server_block(content: str) -> str:
    """Remove the open-skills entry from mcp_servers: in YAML, preserving comments."""
    lines = content.splitlines(keepends=True)
    result = []
    skip = False
    entry_indent = None
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(f"{SERVER_ENTRY_NAME}:") and not skip:
            cur_indent = len(line) - len(stripped)
            entry_indent = cur_indent
            skip = True
            continue
        if skip:
            if stripped and not stripped.startswith("#"):
                cur_indent = len(line) - len(stripped)
                if cur_indent <= entry_indent:
                    skip = False
            elif not stripped.strip():
                pass
            else:
                continue
        if not skip:
            result.append(line)
    return "".join(result)


def _connect_agent_yaml(
    target_path: Path, old_content: str, entry: dict, dry_run: bool, agent_id: str,
) -> dict[str, Any]:
    """Handle connect for YAML-format configs (Hermes). Text-based to preserve comments."""
    import yaml
    try:
        config = _read_yaml_config(target_path) if old_content else {}
    except ValueError as e:
        return {"action": "failed", "path": str(target_path), "error": str(e)}

    servers = config.get("mcp_servers") or {}
    was_installed = SERVER_ENTRY_NAME in servers
    action = "updated" if was_installed else "installed"

    args_yaml = json.dumps(entry["args"])
    entry_lines = f"  {SERVER_ENTRY_NAME}:\n    command: \"{entry['command']}\"\n    args: {args_yaml}\n"

    if was_installed:
        cleaned = _remove_yaml_server_block(old_content)
    else:
        cleaned = old_content

    if "mcp_servers:" in cleaned:
        idx = cleaned.index("mcp_servers:")
        end_of_line = cleaned.index("\n", idx) + 1
        new_content = cleaned[:end_of_line] + entry_lines + cleaned[end_of_line:]
    else:
        new_content = cleaned.rstrip("\n") + "\n\nmcp_servers:\n" + entry_lines

    diff = _generate_diff(old_content, new_content) if old_content else None

    if dry_run:
        return {"action": action, "path": str(target_path), "diff": diff or new_content}

    backup = _backup_file(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(new_content)

    try:
        verify = yaml.safe_load(target_path.read_text())
        if not isinstance(verify, dict):
            raise ValueError("Verified content is not a dict")
    except Exception as e:
        if backup and backup.exists():
            shutil.copy2(str(backup), str(target_path))
        return {"action": "failed", "path": str(target_path), "error": f"Write validation failed, rolled back: {e}"}

    logger.info("connect_agent: agent=%s action=%s path=%s", agent_id, action, target_path)
    return {"action": action, "path": str(target_path), "diff": diff}


def disconnect_agent(
    agent_id: str,
    *,
    config_path: Optional[str] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove the Open Skills MCP server entry from an agent's config file.

    Returns dict with action, path, diff (if dry_run).
    """
    if config_path:
        target_path = Path(config_path).expanduser()
        servers_key = "mcpServers"
        fmt = "mcp-json"
    else:
        agent = AGENT_REGISTRY.get(agent_id)
        if not agent:
            return {"action": "failed", "path": "", "error": f"Unknown agent: {agent_id}"}
        target_path = _resolve_agent_config_path(agent_id)
        if target_path is None:
            return {"action": "failed", "path": "", "error": f"No config path for agent '{agent_id}' on this OS"}
        servers_key = agent["servers_key"]
        fmt = agent["format"]

    if not target_path.exists():
        return {"action": "skipped", "path": str(target_path), "error": "Config file does not exist"}

    old_content = target_path.read_text()

    if fmt == "mcp-toml":
        return _disconnect_agent_toml(target_path, old_content, dry_run, agent_id)
    if fmt == "mcp-yaml":
        return _disconnect_agent_yaml(target_path, old_content, dry_run, agent_id)

    try:
        config = json.loads(old_content)
    except json.JSONDecodeError as e:
        return {"action": "failed", "path": str(target_path), "error": f"Config file is not valid JSON: {e}"}

    servers = config.get(servers_key, {})
    if SERVER_ENTRY_NAME not in servers:
        return {"action": "skipped", "path": str(target_path), "error": "Open Skills entry not found"}

    del servers[SERVER_ENTRY_NAME]
    if not servers:
        del config[servers_key]

    new_content = json.dumps(config, indent=2) + "\n"
    diff = _generate_diff(old_content, new_content)

    if dry_run:
        return {"action": "uninstalled", "path": str(target_path), "diff": diff}

    backup = _backup_file(target_path)

    _write_mcp_json_config(target_path, config)

    try:
        verify = json.loads(target_path.read_text())
        if not isinstance(verify, dict):
            raise ValueError("Verified content is not a dict")
    except Exception as e:
        if backup and backup.exists():
            shutil.copy2(str(backup), str(target_path))
        return {"action": "failed", "path": str(target_path), "error": f"Write validation failed, rolled back: {e}"}

    logger.info("disconnect_agent: agent=%s path=%s", agent_id, target_path)
    return {"action": "uninstalled", "path": str(target_path), "diff": diff}


def _disconnect_agent_toml(
    target_path: Path, old_content: str, dry_run: bool, agent_id: str,
) -> dict[str, Any]:
    """Handle disconnect for TOML-format configs (Codex)."""
    try:
        config = _read_toml_config(target_path)
    except ValueError as e:
        return {"action": "failed", "path": str(target_path), "error": str(e)}

    servers = config.get("mcp_servers", {})
    if SERVER_ENTRY_NAME not in servers:
        return {"action": "skipped", "path": str(target_path), "error": "Open Skills entry not found"}

    new_content = _remove_toml_server_section(old_content)
    diff = _generate_diff(old_content, new_content)

    if dry_run:
        return {"action": "uninstalled", "path": str(target_path), "diff": diff}

    backup = _backup_file(target_path)
    target_path.write_text(new_content)

    try:
        import tomllib
        verify = tomllib.loads(target_path.read_text())
        if not isinstance(verify, dict):
            raise ValueError("Verified content is not a dict")
    except Exception as e:
        if backup and backup.exists():
            shutil.copy2(str(backup), str(target_path))
        return {"action": "failed", "path": str(target_path), "error": f"Write validation failed, rolled back: {e}"}

    logger.info("disconnect_agent: agent=%s path=%s", agent_id, target_path)
    return {"action": "uninstalled", "path": str(target_path), "diff": diff}


def _disconnect_agent_yaml(
    target_path: Path, old_content: str, dry_run: bool, agent_id: str,
) -> dict[str, Any]:
    """Handle disconnect for YAML-format configs (Hermes). Text-based to preserve comments."""
    import yaml
    try:
        config = _read_yaml_config(target_path)
    except ValueError as e:
        return {"action": "failed", "path": str(target_path), "error": str(e)}

    servers = config.get("mcp_servers") or {}
    if SERVER_ENTRY_NAME not in servers:
        return {"action": "skipped", "path": str(target_path), "error": "Open Skills entry not found"}

    new_content = _remove_yaml_server_block(old_content)
    diff = _generate_diff(old_content, new_content)

    if dry_run:
        return {"action": "uninstalled", "path": str(target_path), "diff": diff}

    backup = _backup_file(target_path)
    target_path.write_text(new_content)

    try:
        verify = yaml.safe_load(target_path.read_text())
        if not isinstance(verify, dict):
            raise ValueError("Verified content is not a dict")
    except Exception as e:
        if backup and backup.exists():
            shutil.copy2(str(backup), str(target_path))
        return {"action": "failed", "path": str(target_path), "error": f"Write validation failed, rolled back: {e}"}

    logger.info("disconnect_agent: agent=%s path=%s", agent_id, target_path)
    return {"action": "uninstalled", "path": str(target_path), "diff": diff}
