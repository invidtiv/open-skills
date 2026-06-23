# Open Skills

> *The way you work should be yours, not rented back to you.*

Open Skills is a portable skill format, CLI tool, MCP Server, and web UI for AI agent workflows. Your skills — the procedures you've refined for researching, writing, coding, testing, reviewing, and recovering — are leaving your hands. AI turns them into prompts, runbooks, and agent workflows. Open Skills makes sure they stay yours: visible, movable, inspectable, testable, and available wherever you work.

## Scoping & Directory Hierarchy

To prevent procedural drift, skills follow a strict, predictable file hierarchy. We define two distinct scopes:

### Global Scope (Lives in `~/.config/open-skills/`)
```
├── skills/
│   ├── personal-voice/
│   │   ├── skill.md
│   │   └── voice-samples/
│   └── current-search/
│       └── skill.md
└── runbooks/
    └── content-pipeline.md
```

### Local Scope (Lives in `your-project-repo/.open-skills/`)
```
├── skills/
│   ├── browser-qa/
│   │   └── skill.md
│   └── db-migration/
│       └── skill.md
└── runbooks/
    └── release-day.md
```

---

## Anatomy of a `skill.md` File

A skill is a self-contained markdown file parsed by code, not just read by a model. It uses a strict YAML frontmatter block to define its metadata, boundaries, and hooks, followed by standard markdown sections.

```yaml
---
name: browser-qa
description: Verifies frontend changes across responsive breakpoints.
triggers:
  - "on UI change"
  - "before calling a layout task done"
boundaries:
  - "Do not test on production databases."
  - "Never bypass console error checks."
required_tools:
  - headless-browser
  - terminal
output_format: "QA_EVIDENCE.md"
disable-model-invocation: false
user-invocable: true
---

## Objective
Ensure the active route renders correctly on desktop and mobile without runtime errors.

## Procedure
1. Identify the local server port. If not running, start it using `npm run dev`.
2. Open the browser tool and navigate to the modified routes.
3. Change viewport to 375x812 (Mobile) and inspect for overlapping text or broken layouts.

## Verification Contract (NON-NEGOTIABLE)
Your job is NOT done until you provide:
- [ ] Console logs showing zero uncaught exceptions.
- [ ] Saved screenshots of both Desktop and Mobile views in `./qa-artifacts/`.
```

---

## Quick Start

```bash
# Create a new Open Skill in local scope (default) or global scope
python3 openskills.py init my-workflow --local
python3 openskills.py init my-workflow --global

# List all skills in local and global scopes
python3 openskills.py list

# Validate — does it pass the validation anatomy checks?
python3 openskills.py validate my-workflow

# Test — run the skill's unit tests
python3 openskills.py test my-workflow

# Add — import an external skill directory into your scope
python3 openskills.py add /path/to/skill-dir --local
python3 openskills.py add /path/to/skill-dir --global

# Start the local Open Skills MCP Server
python3 openskills.py mcp start

# Extract — pull repeatable procedures from the latest chat logs
python3 openskills.py extract --last-session
```

---

## Runbooks as Composition

Runbooks chain primitive skills together. Instead of code, a runbook acts as a structural state-machine manifesto that instructs the agent how to pipe outputs from one skill to the next.

A runbook defines a phase table:

| Phase | Active Skill | Input | Expected Verified Output |
|---|---|---|---|
| 01 | media-transcriber | Raw audio file | Verified .txt clean transcript |
| 02 | personal-voice | Clean transcript | Markdown draft matching structural voice standards |
| 03 | browser-qa | Local deployment route | Screenshot artifacts + zero console errors |

Manage runbook states across execution restarts:
```bash
# List all runbooks
python3 openskills.py runbook list

# Start a runbook state tracker
python3 openskills.py runbook start release-day

# Show active runbook execution status
python3 openskills.py runbook status

# Advance to the next phase
python3 openskills.py runbook next

# Revert to the previous phase
python3 openskills.py runbook prev

# Reset active runbook state
python3 openskills.py runbook reset
```

---

## Model Context Protocol (MCP) Server

To make these markdown files transportable across Cursor, Claude Code, and Codex, you can run the local Open Skills MCP Server. A lightweight process reads your `.open-skills/` and `~/.config/open-skills/` directories and exposes them dynamically to any active agent session.

- **Dynamic Context Injection**: Exposes the `open-skills-context` prompt to feed all active skills into the agent's system prompt context.
- **Trigger Monitoring**: The `check_triggers` tool scans user queries for keyword overlap against skill triggers to automatically suggest injecting skills.
- **Tools & Resources**: Exposes tools `list_skills`, `get_skill`, `get_runbook_state`, `advance_runbook` and resources like `open-skills://runbook-state`.

---

## Extracting Workflows (The Flywheel)

To prevent brilliant workflows from dying in obscure chat histories, use the extraction CLI:
```bash
python3 openskills.py extract --last-session
```
It retrieves the latest chat session logs from your local tools (e.g. Superpowers SQLite DB or Claude history logs), parses them, resolves OpenRouter API credentials from the environment or `.env` file, calls a completions model (DeepSeek V4 Flash via OpenRouter by default), and dumps a draft skill into `.open-skills/skills/pending-review/` for you to inspect, modify, and commit.

### Configuration

The extract command requires an OpenRouter API key. Set it via environment variable or `.env` file:

```bash
# In .env or your shell environment
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Optional configuration:

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Required for extract. OpenRouter API key. |
| `EXTRACT_MODEL` | `deepseek/deepseek-v4-flash` | Model to use for extraction. |
| `EXTRACT_API_BASE` | `https://openrouter.ai/api/v1/chat/completions` | OpenRouter completions endpoint. |

---

## Web UI

Open Skills includes a FastAPI backend (`server.py`) and a React/Vite frontend (`web/`) for managing skills and runbooks through a browser interface.

### Running the Web UI

```bash
# Build the frontend
cd web && npm install && npm run build && cd ..

# Start the backend server
python3 server.py
```

The server runs on `http://localhost:8000` and serves the built SPA at the root path, with API endpoints under `/api`.

### Authentication

By default, the server runs without authentication (suitable for localhost development). To enable shared-secret authentication, set the `OPENSKILLS_API_TOKEN` environment variable:

```bash
export OPENSKILLS_API_TOKEN=your-secret-token
python3 server.py
```

When enabled, all API requests must include an `Authorization: Bearer <token>` header.

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/skills` | List all skills (local + global) |
| GET | `/api/skills/{name}` | Get skill detail (frontmatter, body, files) |
| POST | `/api/skills` | Create a new skill |
| PUT | `/api/skills/{name}` | Save skill (raw markdown) |
| PUT | `/api/skills/{name}/structured` | Save skill (structured frontmatter + body) |
| DELETE | `/api/skills/{name}` | Delete a skill |
| POST | `/api/skills/{name}/validate` | Validate a skill |
| POST | `/api/skills/add` | Import an external skill directory |
| POST | `/api/skills/extract` | Extract a skill from last chat session |
| GET | `/api/skills/{name}/files` | List files in a skill directory |
| GET | `/api/skills/{name}/files/{path}` | Read a file from a skill directory |
| GET | `/api/runbooks` | List all runbooks |
| GET | `/api/runbooks/state` | Get active runbook state |
| POST | `/api/runbooks/{name}/start` | Start a runbook |
| POST | `/api/runbooks/advance` | Advance to next phase |
| POST | `/api/runbooks/prev` | Revert to previous phase |
| POST | `/api/runbooks/reset` | Reset runbook state |

---

## License

MIT. Your skills belong to you. The format belongs to everyone.
