# Open Skills Specification v1.0

## The Problem

Your skills are leaving your hands. The way you research, write, code, test,
review, and recover used to live in you — the standards, the shortcuts, the
taste, the checks. AI is turning that into software: prompts, SKILL.md files,
runbooks, scripts, MCP configs, permission boundaries, and agent workflows.

The thing that used to live in your hands now lives in a harness.

That's the opportunity. It's also the ownership fight. Because if your skills
live outside your hands, they should not belong to the vendor whose tool you
happened to build them in. They should be **yours** — visible, movable,
inspectable, testable, and available wherever you work.

Today almost none of that is true. The prompt copies over. The intention copies
over. The **skill** does not. You rebuild it from memory. A teammate improves
a different copy and never tells you. Your best workflow ends up stranded in
a chat history nobody can find again.

**You are not short on intelligence or context. You are short on a way to carry
the procedure itself.**

---

## What Is an Open Skill?

An Open Skill is a self-contained, vendor-agnostic unit of procedural knowledge
that can be installed, validated, exported, and re-imported across any
AI agent platform without loss of fidelity.

It is not a prompt. It is not a memory. It is not a chat transcript.

| Concept | Lifespan | Survives model change? | Carries procedure? |
|---|---|---|---|
| **Prompt** | One conversation | Yes (text travels) | No (intent without method) |
| **Memory** | Session-limited | Sometimes | No (facts without process) |
| **Skill** | Permanent, portable | **Yes** | **Yes** (full procedure) |

People collapse these three into one. Only the skill survives a model change
with the procedure intact.

---

## The Open Skill Package Format

An Open Skill is a directory containing:

```
my-skill/
├── SKILL.md              # The procedure (portable markdown + YAML frontmatter)
├── manifest.yaml         # Dependencies, permissions, compatibility declarations
├── scripts/              # Executable code the skill calls
│   └── validate.sh
├── templates/            # Reusable output/input templates
│   └── report.md.tmpl
├── references/           # Supporting documentation the skill loads
│   └── api-notes.md
├── tests/                # Verifiable checks that the skill works
│   └── test_basic.py
└── adapters/             # Platform-specific wrappers (auto-generated on export)
    ├── hermes.md
    ├── claude-code.md
    ├── cursor.md
    └── codex.md
```

### SKILL.md — The Procedure

The core file. Written in portable markdown with a YAML frontmatter block that
any platform can parse. Contains the actual procedure: numbered steps, exact
commands, pitfalls, and verification — not just "what to do" but **how to do
it repeatably**.

```yaml
---
name: support-billing-recovery
version: 1.0.0
description: >
  Recover a stuck billing charge for a support ticket: identify the charge,
  verify the failure, issue the refund, document the resolution.
category: operations
tags: [billing, support, refunds, customer-success]
author: you@yourdomain.com
license: MIT
created: 2026-06-19
updated: 2026-06-19
min_agent_capability: tool-use
---
```

The body follows this structure:

1. **Trigger** — When this skill should activate (conditions, keywords, contexts)
2. **Prerequisites** — What must be true before starting (access, tools, data)
3. **Procedure** — Numbered steps with exact commands or actions
4. **Pitfalls** — Known failure modes and how to avoid them
5. **Verification** — How to confirm the skill worked (not "it seems done")
6. **Recovery** — What to do if it goes wrong

### manifest.yaml — The Declaration

```yaml
# Declares what the skill needs and what it touches
dependencies:
  tools:
    - name: stripe-cli
      required: true
      check: "stripe --version"
    - name: curl
      required: true
  data:
    - description: "Active Stripe API key in environment"
      env_var: STRIPE_API_KEY
      required: true
  skills:
    - name: customer-lookup
      version: ">=1.0.0"
      required: false

permissions:
  network: true
  filesystem:
    - path: /tmp/billing-recovery/
      access: write
  api_keys:
    - STRIPE_API_KEY
    - SUPPORT_TICKET_API_KEY

compatibility:
  - platform: hermes
    min_version: "0.9"
  - platform: claude-code
    min_version: "1.0"
  - platform: cursor
    min_version: "0.45"
  - platform: codex
    min_version: "1.0"
  - platform: generic
    notes: "Any agent that can read markdown and execute shell commands"

tests:
  - name: dry-run-validation
    command: "python3 tests/test_basic.py --dry-run"
    expected_exit: 0
  - name: refund-logic-check
    command: "python3 tests/test_basic.py --check-logic"
    expected_exit: 0
```

---

## The Work Package Checklist

This is the test that separates a skill you **own** from a lucky setup you
happened to land in one app. A skill is an Open Skill only if it passes all
eight checks:

| # | Check | Question | Pass |
|---|---|---|---|
| 1 | **Visible** | Can you find it without searching chat history? | ☐ |
| 2 | **Movable** | Can you install it on a different platform in under 5 minutes? | ☐ |
| 3 | **Inspectable** | Can you read the full procedure without running anything? | ☐ |
| 4 | **Testable** | Does it have a verification step that confirms it worked? | ☐ |
| 5 | **Versioned** | Does it have a version number and a changelog? | ☐ |
| 6 | **Dependent-declared** | Are all tool/data/API dependencies listed? | ☐ |
| 7 | **Permission-bounded** | Are its permissions (network, files, keys) explicit? | ☐ |
| 8 | **Platform-agnostic** | Does the core procedure work without platform-specific syntax? | ☐ |

If any check fails, you don't have a skill — you have a habit that will die
the next time you switch tools.

---

## The One-Question Test

> **"If I deleted this app tomorrow, how long would it take me to rebuild
> this workflow somewhere else?"**

- **Under 5 minutes** → You own it. The skill is portable.
- **5–30 minutes** → You partially own it. Some pieces will survive, some won't.
- **Over 30 minutes, or "I'd have to start over"** → You rent it. The vendor owns
  your workflow, and they just haven't charged you for the move yet.

---

## The Skill Debt

The four ways skill breakage shows up at work — the debt you didn't know you
were carrying:

1. **Tool-switch tax**: Every platform change is a full rebuild. The prompt
   copies, the skill doesn't. You pay in time and lost nuance.

2. **Onboarding amnesia**: Every new hire starts from scratch. Your team's best
   workflows live in one person's muscle memory, not in a shared, installable
   library.

3. **Improvement silencing**: One person improves their copy. Nobody else finds
   out. The improvement dies as a private habit instead of propagating.

4. **Chat-history archaeology**: Your best workflow is buried in a conversation
   from three months ago. You can't find it. You can't version it. You can't
   share it. You rebuild it from memory and get it slightly wrong.

This debt compounds. Every tool switch, every new hire, every private
improvement adds to it. The interest is paid in rework, in bugs that were
already fixed elsewhere, in standards that drift.

Open Skills pays down the debt by making the skill the unit of ownership —
not the app, not the chat, not the subscription.

---

## Platform Adapters

The core skill (SKILL.md + manifest.yaml + supporting files) is
platform-agnostic. Platform adapters translate the portable format into
whatever a specific agent expects:

| Platform | Adapter Output | Install Location |
|---|---|---|
| Hermes Agent | SKILL.md (native format) | `~/.hermes/skills/skill-name/` |
| Claude Code | CLAUDE.md or skill markdown | `.claude/skills/skill-name.md` |
| Cursor | `.cursorrules` or rules markdown | `.cursor/rules/skill-name.mdc` |
| Codex | AGENTS.md section or markdown | `codex.md` or project config |
| Generic | SKILL.md as-is | Any directory |

Adapters are **generated**, not maintained. You maintain one skill; the adapter
system produces platform-specific wrappers on export. You never edit
platform-specific files by hand.

---

## License

Open Skills is released under MIT. Your skills belong to you. The format
belongs to everyone.
