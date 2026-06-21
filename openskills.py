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
import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("✗ PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

VERSION = "2.0.0"
SPEC_VERSION = "2.0.0"

# ─── Scoping & Directories ──────────────────────────────────────────────────

def get_global_dir():
    return Path.home() / ".config" / "open-skills"

def get_local_dir():
    curr = Path.cwd().resolve()
    for p in [curr] + list(curr.parents):
        if (p / ".open-skills").is_dir() or (p / ".git").exists():
            return p / ".open-skills"
    return curr / ".open-skills"

def resolve_skill(name):
    # Try local scope
    local_dir = get_local_dir()
    local_skill_dir = local_dir / "skills" / name
    for filename in ["skill.md", "SKILL.md"]:
        if (local_skill_dir / filename).exists():
            return local_skill_dir, local_skill_dir / filename
            
    # Try global scope
    global_dir = get_global_dir()
    global_skill_dir = global_dir / "skills" / name
    for filename in ["skill.md", "SKILL.md"]:
        if (global_skill_dir / filename).exists():
            return global_skill_dir, global_skill_dir / filename
            
    # Fallback to direct path if name is a directory
    p = Path(name)
    if p.is_dir():
        for filename in ["skill.md", "SKILL.md"]:
            if (p / filename).exists():
                return p, p / filename
                
    return None, None

def resolve_runbook(name):
    if not name.endswith(".md"):
        name_ext = f"{name}.md"
    else:
        name_ext = name
        name = name[:-3]
    
    # Try local
    local_rb = get_local_dir() / "runbooks" / name_ext
    if local_rb.exists():
        return local_rb
        
    # Try global
    global_rb = get_global_dir() / "runbooks" / name_ext
    if global_rb.exists():
        return global_rb
        
    # Try direct path
    p = Path(name_ext)
    if p.exists():
        return p
        
    return None

# ─── Helpers ───────────────────────────────────────────────────────────────

def die(msg, code=1):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)

def ok(msg):
    print(f"✓ {msg}")

def info(msg):
    print(f"  {msg}")

def parse_frontmatter(text):
    text = text.lstrip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return fm or {}, body
            except Exception as e:
                print(f"  ⚠ Failed to parse YAML frontmatter: {e}", file=sys.stderr)
    return {}, text

# ─── Init ──────────────────────────────────────────────────────────────────

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

def cmd_init(args):
    if not args:
        die("Usage: openskills init <skill-name> [--global|--local]")
    name = args[0]
    is_global = "--global" in args
    
    safe = re.sub(r'[^a-z0-9-]', '-', name.lower().strip())
    
    if is_global:
        base_dir = get_global_dir()
    else:
        base_dir = get_local_dir()
        
    target_dir = base_dir / "skills" / safe
    if target_dir.exists():
        die(f"Skill directory {target_dir} already exists")
        
    target_dir.mkdir(parents=True, exist_ok=True)
    skill_file = target_dir / "skill.md"
    skill_file.write_text(SKELETON_SKILL.format(name=safe))
    
    # Create empty supporting dirs
    (target_dir / "tests").mkdir(exist_ok=True)
    (target_dir / "tests" / ".gitkeep").write_text("")
    
    ok(f"Created Open Skill '{safe}' at {skill_file}")

# ─── Validate ──────────────────────────────────────────────────────────────

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
        elif p.is_dir():
            for fn in ["skill.md", "SKILL.md"]:
                if (p / fn).exists():
                    skill_file = p / fn
                    skill_dir = p
                    break
    
    if not skill_file or not skill_file.exists():
        die(f"Could not resolve skill target '{target}'")
        
    print(f"\nOpen Skills Validation — {skill_file.name} ({skill_dir.name}/)\n")
    
    content = skill_file.read_text()
    fm, body = parse_frontmatter(content)
    
    errors = []
    
    # Check 1: Frontmatter exists
    if not fm:
        errors.append("Missing or invalid YAML frontmatter block")
        print("  [✗] Frontmatter block exists")
    else:
        print("  [✓] Frontmatter block exists")
        
        # Check fields
        for field in ["name", "description", "triggers", "boundaries", "required_tools", "output_format"]:
            val = fm.get(field)
            if val is None:
                errors.append(f"Frontmatter field '{field}' is missing")
                print(f"  [✗] Frontmatter field '{field}' declared")
            elif field in ["triggers", "boundaries", "required_tools"]:
                if not isinstance(val, list):
                    errors.append(f"Frontmatter field '{field}' must be a list")
                    print(f"  [✗] Frontmatter field '{field}' format is valid")
                else:
                    print(f"  [✓] Frontmatter field '{field}' declared ({len(val)} items)")
            else:
                if not isinstance(val, str) or not val.strip():
                    errors.append(f"Frontmatter field '{field}' must be a non-empty string")
                    print(f"  [✗] Frontmatter field '{field}' format is valid")
                else:
                    print(f"  [✓] Frontmatter field '{field}' declared: '{val}'")
                    
    # Check body sections
    for section in ["## Objective", "## Procedure", "## Verification Contract (NON-NEGOTIABLE)"]:
        if section not in body:
            errors.append(f"Missing required section header '{section}'")
            print(f"  [✗] Section '{section}' exists")
        else:
            print(f"  [✓] Section '{section}' exists")
            
    # Check checklist items in Verification section
    if "## Verification Contract (NON-NEGOTIABLE)" in body:
        parts = body.split("## Verification Contract (NON-NEGOTIABLE)")
        v_section = parts[1]
        checklist = re.findall(r'- \[[ xX]\]', v_section)
        if not checklist:
            errors.append("Verification Contract must contain at least one checklist item (e.g. - [ ])")
            print("  [✗] Verification Contract has checklist items")
        else:
            print(f"  [✓] Verification Contract has checklist items ({len(checklist)} found)")
    else:
        print("  [✗] Verification Contract has checklist items")
        
    print(f"\n  Validation result: {len(errors)} errors found.")
    if not errors:
        ok("This is a valid Open Skill.")
    else:
        for err in errors:
            print(f"    - {err}")
        die("Skill validation failed.")

# ─── List ──────────────────────────────────────────────────────────────────

def cmd_list(args):
    local_dir = get_local_dir()
    global_dir = get_global_dir()
    
    skills = {}
    
    def scan_scope(scope_path, scope_name):
        skills_dir = scope_path / "skills"
        if not skills_dir.is_dir():
            return
        for item in sorted(skills_dir.iterdir()):
            if item.is_dir():
                skill_file = None
                for fn in ["skill.md", "SKILL.md"]:
                    if (item / fn).exists():
                        skill_file = item / fn
                        break
                if skill_file:
                    try:
                        content = skill_file.read_text()
                        fm, _ = parse_frontmatter(content)
                        name = fm.get("name", item.name)
                        skills[name] = {
                            "name": name,
                            "scope": scope_name,
                            "path": skill_file,
                            "description": fm.get("description", "No description"),
                            "triggers": fm.get("triggers", []),
                            "required_tools": fm.get("required_tools", [])
                        }
                    except Exception as e:
                        info(f"Failed to parse {skill_file}: {e}")
                        
    scan_scope(global_dir, "Global")
    scan_scope(local_dir, "Local")
    
    if not skills:
        print("No Open Skills found.")
        return
        
    print(f"Found {len(skills)} Open Skill(s):\n")
    for name, s in sorted(skills.items()):
        print(f"  {name} [{s['scope']}]")
        print(f"    Path: {s['path']}")
        print(f"    Description: {s['description']}")
        if s['triggers']:
            print(f"    Triggers: {', '.join(s['triggers'])}")
        if s['required_tools']:
            print(f"    Tools: {', '.join(s['required_tools'])}")
        print()

# ─── Test ──────────────────────────────────────────────────────────────────

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
    for tf in sorted(test_dir.glob("*.py")):
        info(f"Running {tf.name}...")
        result = subprocess.run([sys.executable, str(tf)], capture_output=True, text=True)
        if result.returncode == 0:
            ok(f"{tf.name} passed")
            if result.stdout.strip():
                print(result.stdout.rstrip())
            ran += 1
        else:
            die(f"{tf.name} failed:\n{result.stderr}\nStdout:\n{result.stdout}")
            
    ok(f"All tests passed for skill '{name}'. ({ran} run)")

# ─── Runbooks ──────────────────────────────────────────────────────────────

def parse_runbook(filepath):
    content = filepath.read_text()
    lines = content.splitlines()
    phases = []
    
    header_found = False
    for line in lines:
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if parts and parts[0] == "":
                parts = parts[1:]
            if parts and parts[-1] == "":
                parts = parts[:-1]
                
            if not header_found:
                if len(parts) >= 4 and "phase" in parts[0].lower() and "skill" in parts[1].lower():
                    header_found = True
                continue
                
            if all(all(c in "-:| " for c in p) for p in parts if p):
                continue
                
            if len(parts) >= 4:
                phases.append({
                    "phase": parts[0],
                    "skill": parts[1],
                    "input": parts[2],
                    "output": parts[3],
                    "status": "pending"
                })
    return phases

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
    local_state_file = get_local_dir() / ".runbook-state"
    
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
        name = args[1]
        rb_file = resolve_runbook(name)
        if not rb_file:
            die(f"Runbook '{name}' not found")
            
        phases = parse_runbook(rb_file)
        if not phases:
            die(f"Could not parse any phases from runbook '{rb_file}' table")
            
        state = {
            "runbook": rb_file.stem,
            "current_phase": phases[0]["phase"],
            "phases": phases,
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        local_state_file.parent.mkdir(parents=True, exist_ok=True)
        local_state_file.write_text(json.dumps(state, indent=2))
        ok(f"Started runbook '{rb_file.stem}' with {len(phases)} phases. Active phase: {state['current_phase']}.")
        
    elif sub == "status":
        if not local_state_file.exists():
            print("No active runbook. Start one using: openskills runbook start <name>")
            return
            
        try:
            state = json.loads(local_state_file.read_text())
        except Exception as e:
            die(f"Failed to read runbook state: {e}")
            
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
        if not local_state_file.exists():
            die("No active runbook state found")
            
        try:
            state = json.loads(local_state_file.read_text())
        except Exception as e:
            die(f"Failed to read state: {e}")
            
        curr_phase = state["current_phase"]
        phases = state["phases"]
        
        idx = -1
        for i, p in enumerate(phases):
            if p["phase"] == curr_phase:
                idx = i
                break
                
        if idx == -1:
            die(f"Active phase '{curr_phase}' not found in phases list")
            
        phases[idx]["status"] = "completed"
        
        if idx + 1 < len(phases):
            state["current_phase"] = phases[idx + 1]["phase"]
            state["updated_at"] = datetime.datetime.now().isoformat()
            local_state_file.write_text(json.dumps(state, indent=2))
            ok(f"Phase {curr_phase} marked completed. Advanced to Phase {state['current_phase']}: {phases[idx+1]['skill']}")
        else:
            state["current_phase"] = None
            state["updated_at"] = datetime.datetime.now().isoformat()
            local_state_file.write_text(json.dumps(state, indent=2))
            ok(f"Phase {curr_phase} marked completed. Runbook '{state['runbook']}' is now FULLY COMPLETED! 🎉")
            
    elif sub == "prev":
        if not local_state_file.exists():
            die("No active runbook state found")
            
        try:
            state = json.loads(local_state_file.read_text())
        except Exception as e:
            die(f"Failed to read state: {e}")
            
        curr_phase = state["current_phase"]
        phases = state["phases"]
        
        if curr_phase is None:
            idx = len(phases)
        else:
            idx = -1
            for i, p in enumerate(phases):
                if p["phase"] == curr_phase:
                    idx = i
                    break
                    
        if idx == -1:
            die(f"Active phase '{curr_phase}' not found")
            
        if idx > 0:
            new_idx = idx - 1
            state["current_phase"] = phases[new_idx]["phase"]
            phases[new_idx]["status"] = "pending"
            if idx < len(phases):
                phases[idx]["status"] = "pending"
            state["updated_at"] = datetime.datetime.now().isoformat()
            local_state_file.write_text(json.dumps(state, indent=2))
            ok(f"Reverted to Phase {state['current_phase']}: {phases[new_idx]['skill']}")
        else:
            die("Already at the first phase")
            
    elif sub == "reset":
        if local_state_file.exists():
            local_state_file.unlink()
            ok("Runbook state reset successfully.")
        else:
            info("No active runbook to reset.")
            
    else:
        die(f"Unknown runbook subcommand '{sub}'")

# ─── Extractor ─────────────────────────────────────────────────────────────

def get_last_session_transcript():
    # Attempt 1: Superpowers SQLite DB
    db_path = Path.home() / ".config" / "superpowers" / "conversation-index" / "db.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT session_id, max(timestamp) FROM exchanges GROUP BY session_id ORDER BY max(timestamp) DESC LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                session_id = row[0]
                cursor.execute("SELECT user_message, assistant_message FROM exchanges WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
                rows = cursor.fetchall()
                if rows:
                    transcript = []
                    for user, assistant in rows:
                        transcript.append(f"User: {user}")
                        transcript.append(f"Assistant: {assistant}")
                    conn.close()
                    return "\n\n".join(transcript)
            conn.close()
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to read from Superpowers DB: {e}\n")
            
    # Attempt 2: ~/.claude/history.jsonl
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

def get_openai_api_key():
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    
    # Try ~/.openclaw/openclaw.json first for active keys
    config_file = Path.home() / ".openclaw" / "openclaw.json"
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
            whisper_key = config.get("skills", {}).get("entries", {}).get("openai-whisper-api", {}).get("apiKey")
            if whisper_key:
                return whisper_key
            image_key = config.get("skills", {}).get("entries", {}).get("openai-image-gen", {}).get("apiKey")
            if image_key:
                return image_key
        except Exception:
            pass
            
    # Try ~/.openclaw/.env as fallback
    env_file = Path.home() / ".openclaw" / ".env"
    if env_file.exists():
        try:
            text = env_file.read_text()
            m = re.search(r'OPENAI_API_KEY\s*=\s*([^\s]+)', text)
            if m:
                return m.group(1).strip()
        except Exception:
            pass
    return None

def call_openai_chat_completions(api_key, transcript):
    import urllib.request
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    system_message = (
        "You are an expert technical writer and AI systems engineer.\n"
        "Your task is to analyze the following chat transcript between a User and an Assistant.\n"
        "Identify any repeatable, non-obvious technical procedures used or discussed in the chat.\n"
        "Format the output strictly as an Open Skill markdown file.\n\n"
        "The output MUST contain:\n"
        "1. A YAML frontmatter block enclosed in --- at the very top:\n"
        "---\n"
        "name: <slugified-skill-name>\n"
        "description: <concise-description>\n"
        "triggers:\n"
        "  - \"<trigger-condition-1>\"\n"
        "boundaries:\n"
        "  - \"<boundary-condition-1>\"\n"
        "required_tools:\n"
        "  - <tool-1>\n"
        "output_format: \"<expected-output-format-e.g.-QA_EVIDENCE.md-or-plaintext>\"\n"
        "---\n\n"
        "2. A Markdown body with these exact headers:\n"
        "## Objective\n"
        "<Description of the objective of this skill>\n\n"
        "## Procedure\n"
        "1. <Step 1>\n"
        "2. <Step 2>\n\n"
        "## Verification Contract (NON-NEGOTIABLE)\n"
        "Your job is NOT done until you provide:\n"
        "- [ ] <Checklist item 1>\n"
        "- [ ] <Checklist item 2>\n\n"
        "Do not wrap the response in markdown code blocks like ```markdown. "
        "Respond ONLY with the raw markdown text starting with ---."
    )
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Here is the chat transcript:\n\n{transcript}\n\nApply the instructions and extract the skill."}
        ],
        "temperature": 0.2
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        die(f"OpenAI API call failed: {e}")

def extract_skill_name_from_md(md_content):
    fm, _ = parse_frontmatter(md_content)
    name = fm.get("name")
    if name:
        return re.sub(r'[^a-z0-9-]', '-', name.lower().strip())
    return "extracted-skill"

def cmd_extract(args):
    if not args or args[0] != "--last-session":
        die("Usage: openskills extract --last-session")
        
    print("Retrieving latest session chat logs...")
    transcript = get_last_session_transcript()
    if not transcript:
        die("Could not find any recent chat logs in Superpowers database or Claude history log.")
        
    print(f"Retrieved session log (length: {len(transcript)} characters).")
    
    api_key = get_openai_api_key()
    if not api_key:
        die("Could not find OpenAI API key. Please set OPENAI_API_KEY environment variable or define it in ~/.openclaw/.env.")
        
    print("Calling OpenAI API to extract repeatable procedures...")
    skill_content = call_openai_chat_completions(api_key, transcript)
    
    name = extract_skill_name_from_md(skill_content)
    
    pending_dir = get_local_dir() / "skills" / "pending-review" / name
    pending_dir.mkdir(parents=True, exist_ok=True)
    
    skill_file = pending_dir / "skill.md"
    skill_file.write_text(skill_content)
    
    ok(f"Extracted skill '{name}' and wrote draft to: {skill_file}")
    info("You can now review, modify, and commit it.")

# ─── MCP Starter ───────────────────────────────────────────────────────────

def cmd_mcp(args):
    if not args or args[0] != "start":
        die("Usage: openskills mcp start")
    server_path = Path(__file__).parent / "mcp_server.py"
    if not server_path.exists():
        die("mcp_server.py not found")
    print("Starting Open Skills MCP Server...")
    subprocess.run([sys.executable, str(server_path)])

# ─── Score (Legacy) ────────────────────────────────────────────────────────

def _read_fm_body(d):
    for fn in ["skill.md", "SKILL.md"]:
        fp = d / fn
        if fp.exists():
            try:
                return parse_frontmatter(fp.read_text())
            except Exception:
                pass
    return {}, ""

CHECKS = [
    ("visible", "Can you find it without searching chat history?",
     lambda d: any((d / fn).exists() for fn in ["skill.md", "SKILL.md"])),
    ("movable", "Can you install it on a different platform in under 5 minutes?",
     lambda d: bool(_read_fm_body(d)[0].get("name"))),
    ("inspectable", "Can you read the full procedure without running anything?",
     lambda d: any((d / fn).exists() and (d / fn).stat().st_size > 200 for fn in ["skill.md", "SKILL.md"])),
    ("testable", "Does it have a verification step that confirms it worked?",
     lambda d: "## Verification Contract (NON-NEGOTIABLE)" in _read_fm_body(d)[1]),
    ("versioned", "Does it have a version number?",
     lambda d: "version" in _read_fm_body(d)[0] or "name" in _read_fm_body(d)[0]),
    ("deps-declared", "Are all tool/data/API dependencies listed?",
     lambda d: "required_tools" in _read_fm_body(d)[0]),
    ("perm-bounded", "Are its permissions explicit?",
     lambda d: "boundaries" in _read_fm_body(d)[0]),
    ("platform-agnostic", "Does the core work without platform-specific syntax?",
     lambda d: not any(b in _read_fm_body(d)[1] for b in [".cursorrules", "CLAUDE.md", "codex.md"])),
]

def cmd_score(args):
    if not args:
        die("Usage: openskills score <skill-dir>")
    d = Path(args[0])
    passed = 0
    for key, q, fn in CHECKS:
        if fn(d):
            passed += 1
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

# ─── Export & Install & Graph (Legacy) ──────────────────────────────────────

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
    d = Path(args[0])
    platform = args[1]
    if platform not in ADAPTERS:
        die(f"Unknown platform '{platform}'. Available: {', '.join(ADAPTERS)}")
    
    skill_file = None
    for fn in ["skill.md", "SKILL.md"]:
        if (d / fn).exists():
            skill_file = d / fn
            break
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
    if platform == "hermes":
        return Path(home) / ".hermes" / "skills"
    if platform == "claude-code":
        return Path(cwd) / ".claude" / "skills"
    if platform == "cursor":
        return Path(cwd) / ".cursor" / "rules"
    if platform == "codex":
        return Path(cwd)
    if platform == "generic":
        return Path(home) / "open-skills" / "installed"
    return None

def cmd_install(args):
    if len(args) < 2:
        die("Usage: openskills install <platform> <skill-dir>")
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
    d = Path(args[0])
    skill_file = None
    for fn in ["skill.md", "SKILL.md"]:
        if (d / fn).exists():
            skill_file = d / fn
            break
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

# ─── Main ──────────────────────────────────────────────────────────────────

COMMANDS = {
    "init": cmd_init,
    "validate": cmd_validate,
    "list": cmd_list,
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
