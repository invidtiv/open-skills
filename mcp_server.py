"""
Open Skills MCP Server — exposes skills, runbooks, and triggers via MCP.

Uses core.py for all shared logic (no duplication with the CLI).
"""
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.resolve()))

import core

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Open Skills")


# ── Resources ───────────────────────────────────────────────────────────────

@mcp.resource("open-skills://skills/local/{name}")
def get_local_skill_resource(name: str) -> str:
    """Read a local skill's markdown content."""
    local_dir = core.get_local_dir()
    skill_dir = core._safe_child(local_dir / "skills", name)
    fp = core.find_skill_file(skill_dir)
    if fp:
        return fp.read_text()
    raise ValueError(f"Local skill '{name}' not found")


@mcp.resource("open-skills://skills/global/{name}")
def get_global_skill_resource(name: str) -> str:
    """Read a global skill's markdown content."""
    global_dir = core.get_global_dir()
    skill_dir = core._safe_child(global_dir / "skills", name)
    fp = core.find_skill_file(skill_dir)
    if fp:
        return fp.read_text()
    raise ValueError(f"Global skill '{name}' not found")


@mcp.resource("open-skills://runbooks/local/{name}")
def get_local_runbook_resource(name: str) -> str:
    """Read a local runbook's content."""
    local_dir = core.get_local_dir()
    fp = core._safe_child(local_dir / "runbooks", f"{name}.md")
    if fp.exists():
        return fp.read_text()
    raise ValueError(f"Local runbook '{name}' not found")


@mcp.resource("open-skills://runbooks/global/{name}")
def get_global_runbook_resource(name: str) -> str:
    """Read a global runbook's content."""
    global_dir = core.get_global_dir()
    fp = core._safe_child(global_dir / "runbooks", f"{name}.md")
    if fp.exists():
        return fp.read_text()
    raise ValueError(f"Global runbook '{name}' not found")


@mcp.resource("open-skills://runbook-state")
def get_runbook_state_resource() -> str:
    """Get the active runbook state."""
    state = core.read_runbook_state()
    if state:
        return json.dumps(state, indent=2)
    return json.dumps({"status": "no active runbook"})


# ── Prompt ──────────────────────────────────────────────────────────────────

@mcp.prompt("open-skills-context")
def open_skills_context_prompt() -> str:
    """Inject all active skills and procedures into the context."""
    prompt_lines = [
        "# AVAILABLE TECHNICAL PROCEDURES (OPEN SKILLS)",
        "The following repeatable procedures are available in this environment. ",
        "When performing tasks that match their objective or triggers, you MUST follow them.",
        "",
    ]

    skills, _ = core.get_all_skills()

    for s in skills:
        prompt_lines.append(f"## Skill: {s['name']} ({s['scope']})")
        prompt_lines.append(f"Description: {s['description']}")
        if s["triggers"]:
            prompt_lines.append(f"Triggers: {', '.join(s['triggers'])}")
        if s["boundaries"]:
            prompt_lines.append("Boundaries / Rules:")
            for b in s["boundaries"]:
                prompt_lines.append(f"  - {b}")
        if s["required_tools"]:
            prompt_lines.append(f"Required Tools: {', '.join(s['required_tools'])}")
        prompt_lines.append("")
        prompt_lines.append(s["body"])
        prompt_lines.append("-" * 40)
        prompt_lines.append("")

    state = core.read_runbook_state()
    if state and state.get("current_phase"):
        prompt_lines.append("## ACTIVE RUNBOOK TRACKING")
        prompt_lines.append(f"You are currently executing the runbook '{state['runbook']}'.")
        prompt_lines.append(f"Current Active Phase: {state['current_phase']}")
        for p in state["phases"]:
            if p["phase"] == state["current_phase"]:
                prompt_lines.append(f"  - Active Skill: {p['skill']}")
                prompt_lines.append(f"  - Active Input: {p['input']}")
                prompt_lines.append(f"  - Expected Output: {p['output']}")
        prompt_lines.append("")

    return "\n".join(prompt_lines)


# ── Tools ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_skills() -> str:
    """List all available skills (local and global) with metadata."""
    skills, _ = core.get_all_skills()
    serializable = []
    for s in skills:
        serializable.append({
            "name": s["name"],
            "scope": s["scope"],
            "description": s["description"],
            "triggers": s["triggers"],
            "boundaries": s["boundaries"],
            "required_tools": s["required_tools"],
            "output_format": s["output_format"],
        })
    return json.dumps(serializable, indent=2)


@mcp.tool()
def get_skill(name: str) -> str:
    """Get the full markdown content of a skill by name."""
    _, fp = core.resolve_skill(name)
    if fp and fp.exists():
        return fp.read_text()
    return f"Error: Skill '{name}' not found"


@mcp.tool()
def check_triggers(prompt: str) -> str:
    """Scan the user prompt for matching triggers and suggest skills."""
    matches = core.match_triggers(prompt)
    if matches:
        return json.dumps({
            "status": "matches_found",
            "message": f"Found {len(matches)} matching skill(s) based on your prompt triggers.",
            "matches": matches,
        }, indent=2)
    return json.dumps({"status": "no_matches", "message": "No matching skill triggers found"}, indent=2)


@mcp.tool()
def get_runbook_state() -> str:
    """Get the current runbook execution status."""
    state = core.read_runbook_state()
    if state:
        return json.dumps(state, indent=2)
    return json.dumps({"status": "inactive", "message": "No runbook currently active"})


@mcp.tool()
def advance_runbook() -> str:
    """Advance the active runbook to the next phase."""
    result = core.advance_runbook()
    return json.dumps(result, indent=2, default=str)


if __name__ == "__main__":
    mcp.run()
