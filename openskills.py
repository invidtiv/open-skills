#!/usr/bin/env python3
"""
openskills — the CLI for portable agent skills.

Commands:
  init <name> [--global|--local] Scaffold a new Open Skill
  validate <target>              Validate a skill against the anatomy spec
  list                           List all skills in Local and Global scopes
  test <skill-name>              Run tests for a skill
  runbook <subcommand>           Manage runbook state machine (list, start, status, next, prev, reset)
  extract --last-session         Extract new skill draft from last chat session
  mcp start                      Start the local MCP server
  score <skill-dir>              Compute the one-question test score (legacy)
  export <skill-dir> <platform>  Export skill to platform adapter (legacy)
  install <platform> <skill-dir> Install skill into platform (legacy)
  graph <skill-dir>              Show skill dependency graph (legacy)
"""
import sys
import os
import json
import shutil
import subprocess
import re
from pathlib import Path

from core import (
    VERSION,
    SKELETON_SKILL,
    slugify,
    validate_skill_content,
    get_global_dir,
    get_local_dir,
    resolve_skill,
    resolve_runbook,
    parse_frontmatter,
    find_skill_file,
    scan_skills,
    get_all_skills,
    parse_runbook,
    get_runbook_state_file,
    read_runbook_state,
    start_runbook,
    advance_runbook,
    prev_runbook,
    reset_runbook,
)

try:
    import yaml
except ImportError:
    print("✗ PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ── LLM config for extract ─────────────────────────────────────────────────

EXTRACT_API_BASE = "https://openrouter.ai/api/v1/chat/completions"
EXTRACT_MODEL = "deepseek/deepseek-v4-flash"

# ── Helpers ─────────────────────────────────────────────────────────────────

def die(msg, code=1):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)

def ok(msg):
    print(f"✓ {msg}")

def info(msg):
    print(f"  {msg}")

def _warn_legacy(cmd_name):
    print(f"  ⚠ '{cmd_name}' is a legacy command and will be removed in v3.0.", file=sys.stderr)

# ── Init ────────────────────────────────────────────────────────────────────

def cmd_init(args):
    if not args:
        die("Usage: openskills init <skill-name> [--global|--local]")
    name = args[0]
    is_global = "--global" in args

    try:
        safe = slugify(name)
    except ValueError:
        die(f"Invalid skill name '{name}': slugified result is empty")

    base_dir = get_global_dir() if is_global else get_local_dir()
    target_dir = base_dir / "skills" / safe
    if target_dir.exists():
        die(f"Skill directory {target_dir} already exists")

    target_dir.mkdir(parents=True)
    skill_file = target_dir / "skill.md"
    skill_file.write_text(SKELETON_SKILL.format(name=safe))

    (target_dir / "tests").mkdir(exist_ok=True)
    (target_dir / "tests" / ".gitkeep").write_text("")

    ok(f"Created Open Skill '{safe}' at {skill_file}")

# ── Validate ────────────────────────────────────────────────────────────────

def cmd_validate(args):
    if not args:
        die("Usage: openskills validate <skill-name-or-dir-or-file>")
    target = args[0]

    skill_dir, skill_file = resolve_skill(target)
    if not skill_file:
        p = Path(target)
        if p.is_file():
            skill_file = p
            skill_dir = p.parent

    if not skill_file or not skill_file.exists():
        die(f"Could not resolve skill target '{target}'")

    print(f"\nOpen Skills Validation — {skill_file.name} ({skill_dir.name}/)\n")

    content = skill_file.read_text()
    result = validate_skill_content(content)

    for check in result["checks"]:
        mark = "✓" if check["passed"] else "✗"
        detail = f" ({check['detail']})" if check.get("detail") else ""
        print(f"  [{mark}] {check['label']}{detail}")

    errors = result["errors"]
    print(f"\n  Validation result: {len(errors)} errors found.")
    if not errors:
        ok("This is a valid Open Skill.")
    else:
        for err in errors:
            print(f"    - {err}")
        die("Skill validation failed.")

# ── List ────────────────────────────────────────────────────────────────────

def cmd_list(args):
    skills, shadowed = get_all_skills()

    if not skills:
        print("No Open Skills found.")
        return

    print(f"Found {len(skills)} Open Skill(s):\n")
    for s in sorted(skills, key=lambda x: x["name"]):
        shadow_note = " (shadows global)" if s["name"] in shadowed and s["scope"] == "Local" else ""
        print(f"  {s['name']} [{s['scope']}]{shadow_note}")
        print(f"    Path: {s['path']}")
        print(f"    Description: {s['description']}")
        if s['triggers']:
            print(f"    Triggers: {', '.join(s['triggers'])}")
        if s['required_tools']:
            print(f"    Tools: {', '.join(s['required_tools'])}")
        print()

# ── Test ────────────────────────────────────────────────────────────────────

def cmd_test(args):
    if not args:
        die("Usage: openskills test <skill-name>")
    name = args[0]
    skill_dir, skill_file = resolve_skill(name)
    if not skill_dir:
        die(f"Skill '{name}' not found")

    test_dir = skill_dir / "tests"
    if not test_dir.exists() or not any(test_dir.iterdir()):
        die(f"No tests found in {test_dir}")

    ran = 0
    for tf in sorted(test_dir.rglob("*.py")):
        info(f"Running {tf.name}...")
        result = subprocess.run(
            [sys.executable, str(tf)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            ok(f"{tf.name} passed")
            if result.stdout.strip():
                print(result.stdout.rstrip())
            ran += 1
        else:
            die(f"{tf.name} failed:\n{result.stderr}\nStdout:\n{result.stdout}")

    ok(f"All tests passed for skill '{name}'. ({ran} run)")

# ── Runbooks ────────────────────────────────────────────────────────────────

def cmd_runbook(args):
    if not args:
        print("Usage: openskills runbook <subcommand> [args]\n")
        print("Subcommands:")
        print("  list               List all available runbooks")
        print("  start <name>       Start a runbook and initialize state")
        print("  status             Show active runbook execution status")
        print("  next               Advance to the next phase")
        print("  prev               Go back to the previous phase")
        print("  reset              Reset the active runbook state")
        return

    sub = args[0]

    if sub == "list":
        local_dir = get_local_dir() / "runbooks"
        global_dir = get_global_dir() / "runbooks"

        print("Available Runbooks:\n")
        found = False
        if local_dir.is_dir():
            for f in sorted(local_dir.glob("*.md")):
                print(f"  {f.stem} [Local]")
                found = True
        if global_dir.is_dir():
            for f in sorted(global_dir.glob("*.md")):
                print(f"  {f.stem} [Global]")
                found = True
        if not found:
            print("  No runbooks found.")

    elif sub == "start":
        if len(args) < 2:
            die("Usage: openskills runbook start <runbook-name>")
        result = start_runbook(args[1])
        if result["status"] == "error":
            die(result["message"])
        ok(result["message"])

    elif sub == "status":
        state = read_runbook_state()
        if not state:
            print("No active runbook. Start one using: openskills runbook start <name>")
            return

        print(f"\nActive Runbook: {state['runbook']}")
        print(f"Status Updated: {state['updated_at']}\n")

        active_phase = state.get("current_phase")

        print(f"{'Phase':<6} | {'Active Skill':<20} | {'Input':<25} | {'Expected Output':<35} | {'Status':<10}")
        print("-" * 110)

        for p in state["phases"]:
            marker = "▶" if p["phase"] == active_phase else " "
            status_str = "active" if p["phase"] == active_phase else p.get("status", "pending")
            print(f"{marker} {p['phase']:<4} | {p['skill']:<20} | {p['input']:<25} | {p['output']:<35} | {status_str:<10}")
        print()

    elif sub == "next":
        result = advance_runbook()
        if result["status"] == "error":
            die(result["message"])
        ok(result["message"])

    elif sub == "prev":
        result = prev_runbook()
        if result["status"] == "error":
            die(result["message"])
        ok(result["message"])

    elif sub == "reset":
        result = reset_runbook()
        ok(result["message"])

    else:
        die(f"Unknown runbook subcommand '{sub}'")

# ── Extractor ───────────────────────────────────────────────────────────────

def get_last_session_transcript():
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
            sys.stderr.write(f"Warning: Failed to read from Superpowers DB: {e}\n")

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
            sys.stderr.write(f"Warning: Failed to read from Claude history log: {e}\n")

    return None


def get_api_key():
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


def call_llm_completion(api_key, transcript):
    """Call OpenRouter API to extract a skill from a transcript."""
    import urllib.request

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    system_message = (
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

    data = {
        "model": EXTRACT_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Here is the chat transcript:\n\n{transcript}\n\nApply the instructions and extract the skill."},
        ],
        "temperature": 0.2,
    }

    req = urllib.request.Request(
        EXTRACT_API_BASE,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"OpenRouter API call failed: {e}")


def extract_skill_name_from_md(md_content):
    fm, _ = parse_frontmatter(md_content)
    name = fm.get("name")
    if name:
        try:
            return slugify(name)
        except ValueError:
            pass
    return "extracted-skill"


def cmd_extract(args):
    if not args or args[0] != "--last-session":
        die("Usage: openskills extract --last-session")

    print("Retrieving latest session chat logs...")
    transcript = get_last_session_transcript()
    if not transcript:
        die("Could not find any recent chat logs in Superpowers database or Claude history log.")

    print(f"Retrieved session log (length: {len(transcript)} characters).")

    api_key = get_api_key()
    if not api_key:
        die("No API key found. Set OPENROUTER_API_KEY environment variable.")

    print(f"Calling OpenRouter ({EXTRACT_MODEL}) to extract repeatable procedures...")
    skill_content = call_llm_completion(api_key, transcript)

    skill_content = re.sub(
        r'\n*CRITICAL RULES:.*', '', skill_content, flags=re.DOTALL,
    ).rstrip() + "\n"

    name = extract_skill_name_from_md(skill_content)

    pending_dir = get_local_dir() / "skills" / "pending-review" / name
    pending_dir.mkdir(parents=True, exist_ok=True)

    skill_file = pending_dir / "skill.md"
    skill_file.write_text(skill_content)

    ok(f"Extracted skill '{name}' and wrote draft to: {skill_file}")
    info("You can now review, modify, and commit it.")

# ── Add (import external skill) ─────────────────────────────────────────────

def cmd_add(args):
    if not args:
        die("Usage: openskills add <path-to-skill-dir> [--local]")
    src = Path(args[0]).resolve()
    is_local = "--local" in args

    skill_file = find_skill_file(src)
    if not skill_file:
        die(f"No skill.md or SKILL.md found in {src}")

    fm, body = parse_frontmatter(skill_file.read_text())
    name = fm.get("name")
    if not name:
        die(f"Skill at {src} has no 'name' field in frontmatter")

    try:
        safe = slugify(name)
    except ValueError:
        die(f"Invalid skill name '{name}': slugified result is empty")
    base_dir = get_local_dir() if is_local else get_global_dir()
    target_dir = base_dir / "skills" / safe

    if target_dir.exists():
        die(f"Skill '{safe}' already exists at {target_dir}. Remove it first or pick a different name.")

    target_dir.mkdir(parents=True)
    shutil.copytree(src, target_dir, dirs_exist_ok=True)

    scope = "Local" if is_local else "Global"
    ok(f"Added skill '{safe}' to {scope} scope at {target_dir}")

# ── MCP Starter ─────────────────────────────────────────────────────────────

def cmd_mcp(args):
    if not args or args[0] != "start":
        die("Usage: openskills mcp start")
    server_path = Path(__file__).parent / "mcp_server.py"
    if not server_path.exists():
        die("mcp_server.py not found")
    print("Starting Open Skills MCP Server...")
    subprocess.run([sys.executable, str(server_path)])

# ── Score (Legacy) ──────────────────────────────────────────────────────────

CHECKS = [
    ("visible", "Can you find it without searching chat history?",
     lambda fm, body, d: any((d / fn).exists() for fn in ["skill.md", "SKILL.md"])),
    ("movable", "Can you install it on a different platform in under 5 minutes?",
     lambda fm, body, d: bool(fm.get("name"))),
    ("inspectable", "Can you read the full procedure without running anything?",
     lambda fm, body, d: any((d / fn).exists() and (d / fn).stat().st_size > 200 for fn in ["skill.md", "SKILL.md"])),
    ("testable", "Does it have a verification step that confirms it worked?",
     lambda fm, body, d: "## Verification Contract (NON-NEGOTIABLE)" in body),
    ("versioned", "Does it have a version number?",
     lambda fm, body, d: "version" in fm or "name" in fm),
    ("deps-declared", "Are all tool/data/API dependencies listed?",
     lambda fm, body, d: "required_tools" in fm),
    ("perm-bounded", "Are its permissions explicit?",
     lambda fm, body, d: "boundaries" in fm),
    ("platform-agnostic", "Does the core work without platform-specific syntax?",
     lambda fm, body, d: not any(b in body for b in [".cursorrules", "CLAUDE.md", "codex.md"])),
]

def cmd_score(args):
    if not args:
        die("Usage: openskills score <skill-dir>")
    _warn_legacy("score")
    d = Path(args[0])

    fp = find_skill_file(d)
    if fp:
        fm, body = parse_frontmatter(fp.read_text())
    else:
        fm, body = {}, ""

    passed = sum(1 for _, _, fn in CHECKS if fn(fm, body, d))
    missing = len(CHECKS) - passed
    if missing == 0:
        estimate = "under 5 minutes"
        verdict = "You own it."
    elif missing <= 3:
        estimate = "5–30 minutes"
        verdict = "Partially owned."
    else:
        estimate = "over 30 minutes (you'd start over)"
        verdict = "You rent it."
    print(f"\nOne-Question Test — {d.name}/\n")
    print(f"  'If I deleted this app tomorrow, how long would it take")
    print(f"   to rebuild this workflow somewhere else?'\n")
    print(f"  Checks passed: {passed}/{len(CHECKS)}")
    print(f"  Rebuild estimate: {estimate}")
    print(f"  Verdict: {verdict}\n")

# ── Export & Install & Graph (Legacy) ────────────────────────────────────────

ADAPTERS = {
    "hermes": {
        "ext": "md",
        "filename": "SKILL.md",
        "wrap": lambda body, fm: f"---\n{yaml.dump(fm, default_flow_style=False, sort_keys=False)}---\n\n{body}",
        "layout": "flat",
    },
    "claude-code": {
        "ext": "md",
        "filename": "CLAUDE.md",
        "wrap": lambda body, fm: f"# {fm.get('name', 'skill')}\n\n<!-- Open Skill v{fm.get('version', '?')} — portable via openskills -->\n\n{body}",
        "layout": "flat",
    },
    "cursor": {
        "ext": "mdc",
        "filename": "skill.mdc",
        "wrap": lambda body, fm: f"---\ndescription: {str(fm.get('description', '')).strip()}\nglobs: []\nalwaysApply: false\n---\n\n{body}",
        "layout": "flat",
    },
    "codex": {
        "ext": "md",
        "filename": "AGENTS.md",
        "wrap": lambda body, fm: f"## {fm.get('name', 'skill')} (v{fm.get('version', '?')})\n\n{body}",
        "layout": "append",
    },
    "generic": {
        "ext": "md",
        "filename": "SKILL.md",
        "wrap": lambda body, fm: f"---\n{yaml.dump(fm, default_flow_style=False, sort_keys=False)}---\n\n{body}",
        "layout": "flat",
    },
}

def cmd_export(args):
    if len(args) < 2:
        die("Usage: openskills export <skill-dir> <platform>")
    _warn_legacy("export")
    d = Path(args[0])
    platform = args[1]
    if platform not in ADAPTERS:
        die(f"Unknown platform '{platform}'. Available: {', '.join(ADAPTERS)}")

    skill_file = find_skill_file(d)
    if not skill_file:
        die(f"No skill.md or SKILL.md found in {d}")

    md_text = skill_file.read_text()
    fm, body = parse_frontmatter(md_text)
    adapter = ADAPTERS[platform]
    output = adapter["wrap"](body, fm)
    adapter_dir = d / "adapters"
    adapter_dir.mkdir(exist_ok=True)
    outpath = adapter_dir / f"{platform}.{adapter['ext']}"
    outpath.write_text(output)
    ok(f"Exported {d.name} → {platform}: {outpath}")

    plat_support = adapter_dir / platform
    plat_support.mkdir(exist_ok=True)
    for subdir in ["scripts", "templates", "references", "tests"]:
        src = d / subdir
        if src.exists() and any(src.iterdir()):
            dst = plat_support / subdir
            shutil.copytree(src, dst, dirs_exist_ok=True)
    ok(f"Supporting files copied to {plat_support}/")

def _install_target(platform):
    home = str(Path.home())
    cwd = str(Path.cwd())
    targets = {
        "hermes": Path(home) / ".hermes" / "skills",
        "claude-code": Path(cwd) / ".claude" / "skills",
        "cursor": Path(cwd) / ".cursor" / "rules",
        "codex": Path(cwd),
        "generic": Path(home) / "open-skills" / "installed",
    }
    return targets.get(platform)

def cmd_install(args):
    if len(args) < 2:
        die("Usage: openskills install <platform> <skill-dir>")
    _warn_legacy("install")
    platform = args[0]
    d = Path(args[1])
    if platform not in ADAPTERS:
        die(f"Unknown platform. Available: {', '.join(ADAPTERS)}")

    adapter_dir = d / "adapters"
    if not adapter_dir.exists():
        info("No adapters found — generating...")
        cmd_export([str(d), platform])

    target = _install_target(platform)
    if target is None:
        die(f"No install target for {platform}")
    target.mkdir(parents=True, exist_ok=True)
    adapter = ADAPTERS[platform]
    src_adapter = adapter_dir / f"{platform}.{adapter['ext']}"
    if not src_adapter.exists():
        die(f"Adapter file missing: {src_adapter}")

    if adapter["layout"] == "flat":
        dest = target / f"{d.name}.{adapter['ext']}"
        shutil.copy2(src_adapter, dest)
        ok(f"Installed {d.name} → {platform} at {dest}")
    elif adapter["layout"] == "append":
        agents_md = target / "AGENTS.md"
        content = src_adapter.read_text()
        if agents_md.exists():
            existing = agents_md.read_text()
            if d.name not in existing:
                agents_md.write_text(existing + "\n\n" + content)
            else:
                info(f"{d.name} already in AGENTS.md — skipping")
        else:
            agents_md.write_text(content)
        ok(f"Installed {d.name} → {platform} at {agents_md}")

def cmd_graph(args):
    if not args:
        die("Usage: openskills graph <skill-dir>")
    _warn_legacy("graph")
    d = Path(args[0])
    skill_file = find_skill_file(d)
    if not skill_file:
        die(f"No skill.md or SKILL.md found in {d}")

    fm, _ = parse_frontmatter(skill_file.read_text())
    print(f"\nDependency graph — {d.name}/\n")
    print(f"  {d.name}")
    for tool in fm.get("required_tools", []):
        print(f"    ├── tool: {tool} [required]")
    for trigger in fm.get("triggers", []):
        print(f"    ├── trigger: {trigger}")
    for boundary in fm.get("boundaries", []):
        print(f"    ├── boundary: {boundary}")
    print()

# ── Main ────────────────────────────────────────────────────────────────────

COMMANDS = {
    "init": cmd_init,
    "validate": cmd_validate,
    "list": cmd_list,
    "add": cmd_add,
    "test": cmd_test,
    "runbook": cmd_runbook,
    "extract": cmd_extract,
    "mcp": cmd_mcp,
    "score": cmd_score,
    "export": cmd_export,
    "install": cmd_install,
    "graph": cmd_graph,
}

HELP_TEXT = {
    "init":      "Scaffold a new Open Skill (local/global)",
    "validate":  "Validate a skill package or markdown file",
    "list":      "List all skills in Local and Global scopes",
    "add":       "Copy an external skill into Global (or --local) scope",
    "test":      "Run a skill's unit tests",
    "runbook":   "Manage runbook execution (list, start, status, next, prev, reset)",
    "extract":   "Extract procedural skill from latest chat session",
    "mcp":       "Manage the Open Skills MCP Server",
    "score":     "Compute the one-question test score (legacy)",
    "export":    "Generate platform adapter (legacy)",
    "install":   "Install a skill into a platform (legacy)",
    "graph":     "Show skill dependency graph (legacy)",
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(f"openskills v{VERSION} — portable agent skills CLI\n")
        print("Usage: openskills <command> [args]\n")
        print("Commands:")
        for name in COMMANDS:
            print(f"  {name:12} {HELP_TEXT[name]}")
        print(f"\nThe way you work should be yours, not rented back to you.")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        die(f"Unknown command '{cmd}'. Run 'openskills --help'.")
    COMMANDS[cmd](sys.argv[2:])

if __name__ == "__main__":
    main()
