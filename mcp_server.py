"""
Open Skills MCP Server — exposes skills, runbooks, and triggers via MCP.

Uses core.py for all shared logic (no duplication with the CLI).
"""
import sys
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent.resolve()))

import core

from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("Open Skills")

# ── Usage Logging ──────────────────────────────────────────────────────────

LOG_DIR = Path(os.environ.get(
    "OPENSKILLS_LOG_DIR",
    Path.home() / ".config" / "open-skills" / "logs",
))
LOG_FILE = LOG_DIR / "mcp_usage.jsonl"


def _get_client_info(ctx: Context) -> dict:
    """Extract agent identity from MCP session clientInfo if available."""
    try:
        session = ctx.session
        params = session.client_params
        if params and params.clientInfo:
            return {
                "agent_name": params.clientInfo.name,
                "agent_version": params.clientInfo.version,
            }
    except Exception:
        pass
    return {"agent_name": None, "agent_version": None}


def _log_usage(
    tool_name: str,
    args: dict,
    result_summary: str,
    client_info: dict,
    duration_ms: float,
    skill_name: str | None = None,
):
    """Append a usage entry to the JSONL log."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "args": args,
        "skill": skill_name,
        "result_summary": result_summary[:500],
        "duration_ms": round(duration_ms, 1),
        **client_info,
    }
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ── Resources ───────────────────────────────────────────────────────────────

@mcp.resource("open-skills://skills/local/{name}")
def get_local_skill_resource(name: str) -> str:
    """Read a local skill's markdown content."""
    try:
        local_dir = core.get_local_dir()
        skill_dir = core._safe_child(local_dir / "skills", name)
        fp = core.find_skill_file(skill_dir)
        if fp:
            return fp.read_text()
    except ValueError:
        pass
    raise ValueError(f"Local skill '{name}' not found")


@mcp.resource("open-skills://skills/global/{name}")
def get_global_skill_resource(name: str) -> str:
    """Read a global skill's markdown content."""
    try:
        global_dir = core.get_global_dir()
        skill_dir = core._safe_child(global_dir / "skills", name)
        fp = core.find_skill_file(skill_dir)
        if fp:
            return fp.read_text()
    except ValueError:
        pass
    raise ValueError(f"Global skill '{name}' not found")


@mcp.resource("open-skills://runbooks/local/{name}")
def get_local_runbook_resource(name: str) -> str:
    """Read a local runbook's content."""
    try:
        local_dir = core.get_local_dir()
        fp = core._safe_child(local_dir / "runbooks", f"{name}.md")
        if fp.exists():
            return fp.read_text()
    except ValueError:
        pass
    raise ValueError(f"Local runbook '{name}' not found")


@mcp.resource("open-skills://runbooks/global/{name}")
def get_global_runbook_resource(name: str) -> str:
    """Read a global runbook's content."""
    try:
        global_dir = core.get_global_dir()
        fp = core._safe_child(global_dir / "runbooks", f"{name}.md")
        if fp.exists():
            return fp.read_text()
    except ValueError:
        pass
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
    """Inject Open Skills context into the agent system prompt."""
    mode = os.environ.get("OPENSKILLS_CONTEXT_MODE", "index")

    skills, _ = core.get_all_skills()
    skills = [s for s in skills if not s.get("disable_model_invocation", False)]

    if mode == "directive_only":
        prompt_lines = [
            "# AVAILABLE TECHNICAL PROCEDURES (OPEN SKILLS)",
            "You have access to an Open Skills library via the `recommend_skills` tool.",
            "**Before starting any non-trivial task, call `recommend_skills` with a short description of your objective.**",
            "It returns the most relevant skills ranked by relevance. Load the chosen skill with `get_skill` and follow its procedure and verification contract.",
            "Do not attempt to enumerate the full library; use the recommender.",
            "",
        ]
    elif mode == "full":
        prompt_lines = [
            "# AVAILABLE TECHNICAL PROCEDURES (OPEN SKILLS)",
            "The following repeatable procedures are available in this environment. ",
            "When performing tasks that match their objective or triggers, you MUST follow them.",
            "",
        ]
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
    else:
        prompt_lines = [
            "# AVAILABLE TECHNICAL PROCEDURES (OPEN SKILLS)",
            "You have access to an Open Skills library via the `recommend_skills` tool.",
            "**Before starting any non-trivial task, call `recommend_skills` with a short description of your objective.**",
            "It returns the most relevant skills ranked by relevance. Load the chosen skill with `get_skill` and follow its procedure and verification contract.",
            "Do not attempt to enumerate the full library; use the recommender.",
            "",
            "## Skill Index",
            "",
        ]
        for s in skills:
            prompt_lines.append(f"- **{s['name']}** ({s['scope']}): {s.get('description', '')}")
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
def recommend_skills(query: str, limit: int = 5, scope: str = "all", ctx: Context = None) -> str:
    """Given a description of your current task or objective, returns a ranked list of the most relevant Open Skills to use, with relevance scores and short reasons. Call this BEFORE starting a task instead of listing all skills. After choosing, call get_skill to load the full skill."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
    result = core.recommend_skills(query, scope=scope, limit=limit)
    lines = []
    if result["results"]:
        lines.append(f"Top {len(result['results'])} skill(s) for: {query}")
        if result.get("model"):
            lines.append(f"(ranked by {result['model']}, {result['elapsed_ms']}ms)")
        else:
            lines.append(f"(keyword match, {result['elapsed_ms']}ms)")
        lines.append("")
        for i, r in enumerate(result["results"], 1):
            lines.append(f"{i}. {r['name']} [{r['scope']}] — score: {r['score']:.2f}")
            lines.append(f"   {r['reason']}")
            if r.get("triggers"):
                triggers_str = ", ".join(t if isinstance(t, str) else str(t) for t in r["triggers"])
                lines.append(f"   Triggers: {triggers_str}")
            lines.append("")
    else:
        lines.append(f"No skills found for: {query}")
    lines.append("")
    lines.append(json.dumps(result, indent=2))
    top_names = [r["name"] for r in result["results"][:3]]
    _log_usage("recommend_skills", {"query": query, "limit": limit, "scope": scope},
               f"returned {len(result['results'])} results: {top_names}",
               client_info, (time.monotonic() - t0) * 1000)
    return "\n".join(lines)


@mcp.tool()
def list_skills(ctx: Context = None) -> str:
    """List all available skills (local and global) with metadata."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
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
            "disable_model_invocation": s.get("disable_model_invocation", False),
            "user_invocable": s.get("user_invocable", True),
        })
    _log_usage("list_skills", {}, f"returned {len(serializable)} skills",
               client_info, (time.monotonic() - t0) * 1000)
    return json.dumps(serializable, indent=2)


@mcp.tool()
def get_skill(name: str, ctx: Context = None) -> str:
    """Get the full markdown content of a skill by name."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
    _, fp = core.resolve_skill(name)
    if fp and fp.exists():
        content = fp.read_text()
        _log_usage("get_skill", {"name": name}, f"loaded {len(content)} chars",
                   client_info, (time.monotonic() - t0) * 1000, skill_name=name)
        return content
    _log_usage("get_skill", {"name": name}, "not found",
               client_info, (time.monotonic() - t0) * 1000, skill_name=name)
    return f"Error: Skill '{name}' not found"


@mcp.tool()
def check_triggers(prompt: str, ctx: Context = None) -> str:
    """Scan the user prompt for matching triggers and suggest skills."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
    matches = core.match_triggers(prompt)
    if matches:
        match_names = [m["name"] for m in matches]
        _log_usage("check_triggers", {"prompt": prompt[:200]},
                   f"matched: {match_names}", client_info,
                   (time.monotonic() - t0) * 1000)
        return json.dumps({
            "status": "matches_found",
            "message": f"Found {len(matches)} matching skill(s) based on your prompt triggers.",
            "matches": matches,
        }, indent=2)
    _log_usage("check_triggers", {"prompt": prompt[:200]}, "no matches",
               client_info, (time.monotonic() - t0) * 1000)
    return json.dumps({"status": "no_matches", "message": "No matching skill triggers found"}, indent=2)


@mcp.tool()
def get_runbook_state(ctx: Context = None) -> str:
    """Get the current runbook execution status."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
    state = core.read_runbook_state()
    _log_usage("get_runbook_state", {},
               f"active: {state.get('runbook', 'none')}" if state else "inactive",
               client_info, (time.monotonic() - t0) * 1000)
    if state:
        return json.dumps(state, indent=2)
    return json.dumps({"status": "inactive", "message": "No runbook currently active"})


@mcp.tool()
def advance_runbook(ctx: Context = None) -> str:
    """Advance the active runbook to the next phase."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
    result = core.advance_runbook()
    _log_usage("advance_runbook", {}, result.get("action", ""),
               client_info, (time.monotonic() - t0) * 1000)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def start_runbook(name: str, ctx: Context = None) -> str:
    """Start a runbook by name. Initializes the runbook state machine."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
    result = core.start_runbook(name)
    _log_usage("start_runbook", {"name": name}, result.get("action", ""),
               client_info, (time.monotonic() - t0) * 1000)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def prev_runbook(ctx: Context = None) -> str:
    """Revert the active runbook to the previous phase."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
    result = core.prev_runbook()
    _log_usage("prev_runbook", {}, result.get("action", ""),
               client_info, (time.monotonic() - t0) * 1000)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def reset_runbook(ctx: Context = None) -> str:
    """Reset the active runbook state, clearing all progress."""
    t0 = time.monotonic()
    client_info = _get_client_info(ctx) if ctx else {}
    result = core.reset_runbook()
    _log_usage("reset_runbook", {}, result.get("action", ""),
               client_info, (time.monotonic() - t0) * 1000)
    return json.dumps(result, indent=2, default=str)


if __name__ == "__main__":
    mcp.run()
