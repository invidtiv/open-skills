# Open Skills — Voice Chat Briefing

Use this document to brief a voice chat agent on the current state of the Open Skills project so you can brainstorm its future direction.

---

## What Is Open Skills?

Open Skills is a portable skill format and toolchain for AI agent workflows. The core idea: the procedures you've refined for researching, writing, coding, testing, and reviewing should belong to you — not locked inside any single AI platform. A "skill" is a markdown file with YAML frontmatter that any agent can parse, execute, and verify.

The tagline: *The way you work should be yours, not rented back to you.*

## Current State (v3.3.0, June 2026)

### Architecture — Four Surfaces, One Core

```
React SPA (Vite + Tailwind)  ←→  FastAPI REST (server.py :8001)
                                        ↓
CLI (openskills.py)  ──→  core.py (shared logic)  ←──  MCP Server (mcp_server.py)
                                        ↓
                              File System (skills + runbooks + logs)
```

- **core.py** (1,801 lines) — shared logic hub: validation, frontmatter parsing, trigger matching, runbook state machine, LLM extraction pipeline, skill recommendation, category management, agent MCP registration (JSON/TOML/YAML), usage analytics.
- **openskills.py** (820 lines) — CLI: init, validate, test, list, add, extract, connect, recommend, usage. Thin wrapper over core.py.
- **server.py** (711 lines) — FastAPI wrapping core.py as REST. 30+ endpoints including categories and usage analytics. Serves the React SPA. Localhost-only or token auth.
- **mcp_server.py** (361 lines) — Model Context Protocol server exposing skills as tools, resources, and prompts. Logs all tool calls with agent identity tracking via clientInfo. Semantic recommendation and context-mode injection.
- **web/** (~2,010 lines of TypeScript/React) — React 19 + React Router 7 + TanStack Query 5 + Tailwind CSS 4. Pages: Skills browser (with category grouping), Skill detail/editor, Runbooks (with creation UI), Extract, Agent Setup, GitHub import dialog.

### Numbers

- 155 skills in 30 categories across global and local scopes
- 6 agent adapters: Claude Code, Cursor, Windsurf/Devin, Codex (TOML), Hermes (YAML), Kimi
- 3 config formats supported: JSON, TOML, YAML — text-based manipulation preserves comments
- Spec defines 8 validation checks (the "Work Package Checklist")
- The "One-Question Test": *If I deleted this app tomorrow, how long would it take me to rebuild this workflow somewhere else?*

### Key Features

1. **Scoped directories** — Global (`~/.config/open-skills/`) vs Local (`.open-skills/` in repo). Local shadows global.
2. **Skill categories** — Hierarchical folder structure with `DESCRIPTION.md` metadata. GitHub imports auto-categorize by repo owner.
3. **Usage analytics** — JSONL logging of all MCP tool calls with agent identity, skill name, and duration. CLI and REST access to usage stats, including never-used skill detection.
4. **Runbooks** — Markdown tables that chain skills as a state machine. CLI tracks phase execution (start/next/prev/reset).
5. **Session-to-skill extraction** — Reads Claude Code or Superpowers chat logs, calls DeepSeek to extract repeatable procedures as draft skills.
6. **LLM-assisted validation fixes** — When a skill fails validation, the Web UI can request a DeepSeek-generated fix.
7. **GitHub import** — Import skills directly from GitHub repos (full repo, subdirectory, or branch reference). Auto-categorizes by owner.
8. **MCP integration** — Trigger monitoring scans user queries and auto-suggests relevant skills. Context injection in index/full/directive_only modes.
9. **6 agent adapters** — Idempotent MCP registration with backup and dry-run. Supports JSON, TOML, and YAML config formats.

### Recent Development (last few sessions)

- Built the full Web UI from scratch (FastAPI + React SPA)
- Added `openskills add` command for importing external skills
- Extracted shared core module from the monolithic CLI
- Ran all 85 skills through DeepSeek validation/fix pipeline to reach 100% compliance
- Added runbook creation/deletion UI with visual skill picker
- Added GitHub import feature
- **v3.2.0**: Full code review — fixed 3 security issues (git flag injection, auth bypass, delete path safety), moved extraction pipeline from CLI to core.py, added Agent Setup page, added LLM-based skill recommendation
- **v3.3.0**: Skill categories (30 categories, hierarchical folder structure), imported 67 new skills from ~/skills, MCP usage logging with agent identity tracking, usage analytics CLI/API, added Hermes (YAML) and Kimi agent support, TOML config support for Codex, corrected agent config paths

## What's Interesting to Brainstorm

These are open questions and directions — not decisions yet.

### Distribution & Discovery
- How should skills be shared? A registry? A GitHub-based ecosystem? Something decentralized?
- Should there be a "skill store" or curated collections?
- How do you handle versioning and updates when skills are distributed across repos?

### Composition & Orchestration
- Runbooks are currently flat phase tables. Should they support branching/conditionals?
- How do you handle skills that need to communicate state beyond simple output piping?
- Should runbooks be executable (like CI pipelines) or remain declarative manifests?

### Quality & Trust
- The 8-check Work Package Checklist is the quality standard. Is it enough? Too much?
- How do you build trust in community-contributed skills? Reviews? Ratings? Test coverage badges?
- Should there be a "skill debt" score that tracks how stale/unmaintained a skill is?
- Usage analytics now track which skills are never used — what's the right retention policy?

### Scale & Community
- 155 skills across 30 categories is a solid personal library. What happens at 500? 5,000?
- How do you prevent fragmentation when teams fork and modify skills independently?
- Is there a role for AI agents that maintain and improve skills automatically?

### Technical Debt
- No test suite for the web frontend or server endpoints yet (only core.py has 31 unit tests).
- No React error boundary — unhandled throws crash the entire UI.
- Some skills have malformed YAML frontmatter (missing closing `---`) — still parse but emit warnings.

---

*Project repo: /home/bsdev/open-skills — MIT License*
