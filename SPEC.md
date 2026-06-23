# Open Skills Specification v2.0

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
├── skill.md              # The procedure (portable markdown + YAML frontmatter)
├── tests/                # Verifiable checks that the skill works
│   └── test_basic.py
├── adapters/             # Platform-specific wrappers (optional, auto-generated on export)
│   ├── hermes.md
│   ├── claude-code.md
│   ├── cursor.md
│   └── codex.md
├── scripts/              # Optional helper scripts
├── templates/            # Optional file templates
└── references/           # Optional reference materials
```

> **v1.0 → v2.0 change**: The `manifest.yaml` file has been removed. All
> metadata now lives in `skill.md` frontmatter. The directory structure has
> been simplified — `scripts/`, `templates/`, `references/`, and `adapters/`
> are optional and only created if a skill needs them.

### skill.md — The Procedure

The core file. Written in portable markdown with a YAML frontmatter block that
any platform can parse. Contains the actual procedure: numbered steps, exact
commands, pitfalls, and verification — not just "what to do" but **how to do
it repeatably**.

#### Required Frontmatter Fields

```yaml
---
name: support-billing-recovery
description: >
  Recover a stuck billing charge for a support ticket: identify the charge,
  verify the failure, issue the refund, document the resolution.
triggers:
  - "support ticket mentions stuck charge, duplicate billing, or refund request"
  - "billing alert fires for a charge in failed state > 4 hours"
boundaries:
  - "Do not refund succeeded charges"
  - "Do not retry the same declined payment method"
required_tools:
  - stripe-cli
  - curl
output_format: "resolution.json"
---
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Slugified skill name |
| `description` | string | yes | What this skill does |
| `triggers` | list | yes | When to activate this skill |
| `boundaries` | list | yes | What this skill must NOT do |
| `required_tools` | list | yes | Tools/CLIs the skill depends on |
| `output_format` | string | yes | Expected output artifact |

> **Optional fields**: `version`, `category`, `tags`, `author`, `license`,
> `created`, `updated` — these are accepted but not required by validation.

> **Invocation control fields** (optional, boolean, default values shown):
>
> | Field | Default | Description |
> |---|---|---|
> | `disable-model-invocation` | `false` | When `true`, the skill is excluded from automatic trigger matching and context injection. The model will not suggest or auto-activate it — it must be explicitly invoked by the user. |
> | `user-invocable` | `true` | When `false`, the skill cannot be directly invoked by the user. It is only available as a phase in a runbook or via programmatic access. Use this for internal/helper skills that should never be run standalone. |

#### Required Body Sections

The body follows this structure:

1. **## Objective** — What this skill accomplishes
2. **## Procedure** — Numbered steps with exact commands or actions
3. **## Verification Contract (NON-NEGOTIABLE)** — Checklist items (`- [ ]`)
   that confirm the skill worked. Must contain at least one checklist item.

> **Optional sections**: Trigger, Prerequisites, Pitfalls, Recovery — these
> are recommended for complex skills but not required by validation.

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
| 5 | **Dependent-declared** | Are all tool dependencies listed in `required_tools`? | ☐ |
| 6 | **Permission-bounded** | Are its boundaries explicitly declared in `boundaries`? | ☐ |
| 7 | **Platform-agnostic** | Does the core procedure work without platform-specific syntax? | ☐ |
| 8 | **Validated** | Does it pass `openskills validate` with zero errors? | ☐ |

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

The core skill (SKILL.md + supporting files) is
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
