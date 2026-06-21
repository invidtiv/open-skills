import sys
import os
import json
import re
import datetime
from pathlib import Path

# Ensure importing openskills works
sys.path.append(str(Path(__file__).parent.resolve()))

try:
    import openskills
except ImportError as e:
    sys.stderr.write(f"Warning: Could not import openskills: {e}\n")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Open Skills")

@mcp.resource("open-skills://skills/local/{name}")
def get_local_skill_resource(name: str) -> str:
    """Read a local skill's markdown content."""
    local_dir = openskills.get_local_dir()
    local_skill_dir = local_dir / "skills" / name
    for fn in ["skill.md", "SKILL.md"]:
        fp = local_skill_dir / fn
        if fp.exists():
            return fp.read_text()
    raise ValueError(f"Local skill '{name}' not found")

@mcp.resource("open-skills://skills/global/{name}")
def get_global_skill_resource(name: str) -> str:
    """Read a global skill's markdown content."""
    global_dir = openskills.get_global_dir()
    global_skill_dir = global_dir / "skills" / name
    for fn in ["skill.md", "SKILL.md"]:
        fp = global_skill_dir / fn
        if fp.exists():
            return fp.read_text()
    raise ValueError(f"Global skill '{name}' not found")

@mcp.resource("open-skills://runbooks/local/{name}")
def get_local_runbook_resource(name: str) -> str:
    """Read a local runbook's content."""
    local_dir = openskills.get_local_dir()
    fp = local_dir / "runbooks" / f"{name}.md"
    if fp.exists():
        return fp.read_text()
    raise ValueError(f"Local runbook '{name}' not found")

@mcp.resource("open-skills://runbooks/global/{name}")
def get_global_runbook_resource(name: str) -> str:
    """Read a global runbook's content."""
    global_dir = openskills.get_global_dir()
    fp = global_dir / "runbooks" / f"{name}.md"
    if fp.exists():
        return fp.read_text()
    raise ValueError(f"Global runbook '{name}' not found")

@mcp.resource("open-skills://runbook-state")
def get_runbook_state_resource() -> str:
    """Get the active runbook state."""
    state_file = openskills.get_local_dir() / ".runbook-state"
    if state_file.exists():
        return state_file.read_text()
    return json.dumps({"status": "no active runbook"})

@mcp.prompt("open-skills-context")
def open_skills_context_prompt() -> str:
    """Inject all active skills and procedures into the context."""
    local_dir = openskills.get_local_dir()
    global_dir = openskills.get_global_dir()
    
    prompt_lines = [
        "# AVAILABLE TECHNICAL PROCEDURES (OPEN SKILLS)",
        "The following repeatable procedures are available in this environment. ",
        "When performing tasks that match their objective or triggers, you MUST follow them.",
        ""
    ]
    
    skills = []
    
    def add_skills_from_dir(scope_dir, scope_name):
        skills_dir = scope_dir / "skills"
        if not skills_dir.is_dir():
            return
        for item in sorted(skills_dir.iterdir()):
            if item.is_dir():
                for fn in ["skill.md", "SKILL.md"]:
                    fp = item / fn
                    if fp.exists():
                        try:
                            content = fp.read_text()
                            fm, body = openskills.parse_frontmatter(content)
                            skills.append({
                                "name": fm.get("name", item.name),
                                "scope": scope_name,
                                "description": fm.get("description", ""),
                                "triggers": fm.get("triggers", []),
                                "boundaries": fm.get("boundaries", []),
                                "required_tools": fm.get("required_tools", []),
                                "body": body
                            })
                        except Exception:
                            pass
                            
    add_skills_from_dir(global_dir, "Global")
    add_skills_from_dir(local_dir, "Local")
    
    for s in skills:
        prompt_lines.append(f"## Skill: {s['name']} ({s['scope']})")
        prompt_lines.append(f"Description: {s['description']}")
        if s['triggers']:
            prompt_lines.append(f"Triggers: {', '.join(s['triggers'])}")
        if s['boundaries']:
            prompt_lines.append("Boundaries / Rules:")
            for b in s['boundaries']:
                prompt_lines.append(f"  - {b}")
        if s['required_tools']:
            prompt_lines.append(f"Required Tools: {', '.join(s['required_tools'])}")
        prompt_lines.append("")
        prompt_lines.append(s['body'])
        prompt_lines.append("-" * 40)
        prompt_lines.append("")
        
    state_file = openskills.get_local_dir() / ".runbook-state"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            if state.get("current_phase"):
                prompt_lines.append("## ACTIVE RUNBOOK TRACKING")
                prompt_lines.append(f"You are currently executing the runbook '{state['runbook']}'.")
                prompt_lines.append(f"Current Active Phase: {state['current_phase']}")
                for p in state["phases"]:
                    if p["phase"] == state["current_phase"]:
                        prompt_lines.append(f"  - Active Skill: {p['skill']}")
                        prompt_lines.append(f"  - Active Input: {p['input']}")
                        prompt_lines.append(f"  - Expected Output: {p['output']}")
                prompt_lines.append("")
        except Exception:
            pass
            
    return "\n".join(prompt_lines)

@mcp.tool()
def list_skills() -> str:
    """List all available skills (local and global) with metadata."""
    local_dir = openskills.get_local_dir()
    global_dir = openskills.get_global_dir()
    skills = []
    
    def add_skills(s_dir, s_name):
        s_dir = s_dir / "skills"
        if not s_dir.is_dir():
            return
        for item in sorted(s_dir.iterdir()):
            if item.is_dir():
                for fn in ["skill.md", "SKILL.md"]:
                    fp = item / fn
                    if fp.exists():
                        try:
                            fm, _ = openskills.parse_frontmatter(fp.read_text())
                            skills.append({
                                "name": fm.get("name", item.name),
                                "scope": s_name,
                                "description": fm.get("description", ""),
                                "triggers": fm.get("triggers", []),
                                "boundaries": fm.get("boundaries", []),
                                "required_tools": fm.get("required_tools", []),
                                "output_format": fm.get("output_format", "")
                            })
                        except Exception:
                            pass
    add_skills(global_dir, "Global")
    add_skills(local_dir, "Local")
    return json.dumps(skills, indent=2)

@mcp.tool()
def get_skill(name: str) -> str:
    """Get the full markdown content of a skill by name."""
    _, fp = openskills.resolve_skill(name)
    if fp and fp.exists():
        return fp.read_text()
    return f"Error: Skill '{name}' not found"

@mcp.tool()
def check_triggers(prompt: str) -> str:
    """Scan the user prompt for matching triggers of any skill and suggest injecting them."""
    local_dir = openskills.get_local_dir()
    global_dir = openskills.get_global_dir()
    matches = []
    
    def check_dir(s_dir, s_name):
        s_dir = s_dir / "skills"
        if not s_dir.is_dir():
            return
        for item in sorted(s_dir.iterdir()):
            if item.is_dir():
                for fn in ["skill.md", "SKILL.md"]:
                    fp = item / fn
                    if fp.exists():
                        try:
                            fm, body = openskills.parse_frontmatter(fp.read_text())
                            triggers = fm.get("triggers", [])
                            for t in triggers:
                                words = set(re.findall(r'\w+', t.lower()))
                                prompt_words = set(re.findall(r'\w+', prompt.lower()))
                                overlap = words.intersection(prompt_words)
                                
                                if t.lower() in prompt.lower() or (len(words) >= 2 and len(overlap) >= len(words) - 1):
                                    matches.append({
                                        "name": fm.get("name", item.name),
                                        "scope": s_name,
                                        "matched_trigger": t,
                                        "description": fm.get("description", ""),
                                        "suggested_injection": body
                                    })
                                    break
                        except Exception:
                            pass
                            
    check_dir(global_dir, "Global")
    check_dir(local_dir, "Local")
    
    if matches:
        return json.dumps({
            "status": "matches_found",
            "message": f"Found {len(matches)} matching skill(s) based on your prompt triggers.",
            "matches": matches
        }, indent=2)
    return json.dumps({"status": "no_matches", "message": "No matching skill triggers found"}, indent=2)

@mcp.tool()
def get_runbook_state() -> str:
    """Get the current runbook execution status."""
    state_file = openskills.get_local_dir() / ".runbook-state"
    if state_file.exists():
        return state_file.read_text()
    return json.dumps({"status": "inactive", "message": "No runbook currently active"})

@mcp.tool()
def advance_runbook() -> str:
    """Advance the active runbook to the next phase."""
    state_file = openskills.get_local_dir() / ".runbook-state"
    if not state_file.exists():
        return json.dumps({"status": "error", "message": "No active runbook"})
        
    try:
        state = json.loads(state_file.read_text())
        curr_phase = state["current_phase"]
        phases = state["phases"]
        
        idx = -1
        for i, p in enumerate(phases):
            if p["phase"] == curr_phase:
                idx = i
                break
                
        if idx == -1:
            return json.dumps({"status": "error", "message": f"Phase '{curr_phase}' not found"})
            
        phases[idx]["status"] = "completed"
        
        if idx + 1 < len(phases):
            state["current_phase"] = phases[idx + 1]["phase"]
            res_message = f"Advanced to Phase {state['current_phase']}: {phases[idx+1]['skill']}"
        else:
            state["current_phase"] = None
            res_message = f"Runbook '{state['runbook']}' is now fully completed!"
            
        state["updated_at"] = datetime.datetime.now().isoformat()
        state_file.write_text(json.dumps(state, indent=2))
        return json.dumps({"status": "success", "message": res_message, "state": state}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

if __name__ == "__main__":
    # Start mcp server stdio
    mcp.run()
