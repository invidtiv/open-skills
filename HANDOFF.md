# Open Skills — Voice Chat Briefing

Use this document to brief a voice chat agent on the current state of the Open Skills project so you can brainstorm its future direction.

---

## What Is Open Skills?

Open Skills is a portable skill format and toolchain for AI agent workflows. The core idea: the procedures you've refined for researching, writing, coding, testing, and reviewing should belong to you — not locked inside any single AI platform. A "skill" is a markdown file with YAML frontmatter that any agent can parse, execute, and verify.

The tagline: *The way you work should be yours, not rented back to you.*

## Current State (v3.2.0, June 2026)

### Architecture — Four Surfaces, One Core

```
React SPA (Vite + Tailwind)  ←→  FastAPI REST (server.py :8001)
                                        ↓
CLI (openskills.py)  ──→  core.py (shared logic)  ←──  MCP Server (mcp_server.py)
                                        ↓
                              File System (skills + runbooks)
```

- **core.py** (1,296 lines) — shared logic hub: validation, frontmatter parsing, trigger matching, runbook state machine, LLM extraction pipeline, skill recommendation, agent MCP registration.
- **openskills.py** (779 lines) — CLI: init, validate, test, list, add, extract, connect, recommend. Thin wrapper over core.py.
- **server.py** (653 lines) — FastAPI wrapping core.py as REST. 25+ endpoints. Serves the React SPA. Localhost-only or token auth.
- **mcp_server.py** (264 lines) — Model Context Protocol server exposing skills as tools, resources, and prompts to Cursor, Claude Code, Codex, Devin.
- **web/** (~1,590 lines of TypeScript/React) — React 19 + React Router 7 + TanStack Query 5 + Tailwind CSS 4. Pages: Skills browser, Skill detail/editor, Runbooks (with creation UI), Extract, Agent Setup, GitHub import dialog.

### Numbers

- 92 skills in the global library (~85 validated to spec)
- 5 platform adapters: Hermes, Claude Code, Cursor, Codex, Generic
- Spec defines 8 validation checks (the "Work Package Checklist"): Visible, Movable, Inspectable, Testable, Versioned, Deps-declared, Perm-bounded, Platform-agnostic
- The "One-Question Test": *If I deleted this app tomorrow, how long would it take me to rebuild this workflow somewhere else?*

### Key Features

1. **Scoped directories** — Global (`~/.config/open-skills/`) vs Local (`.open-skills/` in repo). Local shadows global.
2. **Runbooks** — Markdown tables that chain skills as a state machine. CLI tracks phase execution (start/next/prev/reset).
3. **Session-to-skill extraction** — Reads Claude Code or Superpowers chat logs, calls DeepSeek to extract repeatable procedures as draft skills.
4. **LLM-assisted validation fixes** — When a skill fails validation, the Web UI can request a DeepSeek-generated fix.
5. **GitHub import** — Import skills directly from GitHub repos (full repo, subdirectory, or branch reference).
6. **MCP integration** — Trigger monitoring scans user queries and auto-suggests relevant skills.

### Recent Development (last few sessions)

- Built the full Web UI from scratch (FastAPI + React SPA)
- Added `openskills add` command for importing external skills
- Extracted shared core module from the monolithic CLI
- Ran all 85 skills through DeepSeek validation/fix pipeline to reach 100% compliance
- Added runbook creation/deletion UI with visual skill picker
- Added GitHub import feature
- Fixed a blank-page crash caused by non-string values in API responses
- Generated a knowledge graph of the codebase (476 nodes, 742 edges, 31 communities)
- Updated the docs site (docs/index.html) to v3.1.0
- **v3.2.0**: Full code review — fixed 3 security issues (git flag injection, auth bypass, delete path safety), moved extraction pipeline from CLI to core.py, added Agent Setup page, added Devin to agent registry, added LLM-based skill recommendation

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

### Platform Adapters
- Currently 5 platforms with static markdown adapters. Should adapters be auto-generated on export?
- New platforms are emerging constantly. How does the adapter story scale?
- Should there be a universal adapter format instead of per-platform?

### The Extraction Flywheel
- Currently extracts from Claude Code and Superpowers logs. What other sources?
- How do you handle extraction from team chat sessions where multiple people contribute?
- Should extraction be continuous (watch mode) or always manual?

### Scale & Community
- 92 skills is a solid personal library. What happens at 500? 5,000?
- How do you prevent fragmentation when teams fork and modify skills independently?
- Is there a role for AI agents that maintain and improve skills automatically?

### Technical Debt
- The graph analysis showed low cohesion in Core Library (0.09), Backend (0.05), and React UI (0.06). Should these be split?
- No test suite for the web frontend or server endpoints yet (only core.py has 31 unit tests).
- No React error boundary — unhandled throws crash the entire UI.

---

*Project repo: /home/bsdev/open-skills — MIT License*
