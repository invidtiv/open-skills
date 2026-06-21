# Open Skills

> *The way you work should be yours, not rented back to you.*

Open Skills is a portable skill format, CLI tool, and Model Context Protocol (MCP) Server for AI agent workflows. Your skills — the procedures you've refined for researching, writing, coding, testing, reviewing, and recovering — are leaving your hands. AI turns them into prompts, runbooks, and agent workflows. Open Skills makes sure they stay yours: visible, movable, inspectable, testable, and available wherever you work.

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
It retrieves the latest chat session logs from your local tools (e.g. Superpowers SQLite DB or Claude history logs), parses them, resolves OpenAI API credentials, calls a local/completions model, and dumps a draft skill into `.open-skills/skills/pending-review/` for you to inspect, modify, and commit.

---

## License

MIT. Your skills belong to you. The format belongs to everyone.
