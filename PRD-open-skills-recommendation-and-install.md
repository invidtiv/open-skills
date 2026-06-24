# PRD — Open Skills: Recommendation, Agent Registration & Web Setup

**Version:** 1.0
**Target release:** v3.2.0
**Date:** 2026-06-24
**Status:** Ready for implementation
**Audience:** Coding agent / implementer
**Repo:** `/home/bsdev/open-skills` (MIT)

---

## 1. Context

Open Skills is a portable skill format + toolchain (CLI `openskills.py`, FastAPI `server.py`, MCP server `mcp_server.py`, React SPA in `web/`, shared `core.py`). It currently catalogs, validates, fixes, and serves skills, and exposes them to agents over MCP.

The library has grown to ~92 skills. The remaining gap is **discovery at scale**. Today an agent either has the entire skill set dumped into context (via the `open-skills-context` prompt) or must manually browse via `list_skills`/`get_skill`. Neither scales: dumping 90+ skills wastes context and is unmanageable, and manual browsing is unreliable because agents skip it.

This PRD specifies the final feature set to turn the library from a passive catalog into an **active, centralized recommender** that any agent can query, plus the distribution mechanism to get agents pointed at the server in the first place.

### The three features

1. **Semantic skill recommendation** — a new MCP tool (`recommend_skills`) backed by a cheap LLM that ranks the most relevant skill(s) for a task, plus a system-prompt hook that instructs agents to call it before starting work.
2. **Agent MCP registration (`connect` CLI command)** — auto-install the Open Skills MCP server entry into known agents' config files (Cursor, devin, Claude Code, Codex, etc.), so agents connect to the live server instead of receiving static skill dumps.
3. **Web "Agent Setup" page** — a frontend page to detect agent installations, show install status, and target manual installation for unknown/unsupported harnesses.

---

## 2. Goals & non-goals

### Goals

- An agent can ask the MCP server "what's the best skill for X?" and get a ranked, scored answer without browsing the full catalog.
- The recommendation hook is injected into the agent's context so the behavior is the default, not opt-in.
- A single CLI command registers the MCP server into the major agent harnesses, idempotently, across macOS/Linux/Windows.
- A web page surfaces detected agents, install status, and a manual-target flow for unknown harnesses.

### Non-goals

- Not building a hosted/remote MCP server — this stays a local (stdio) server for v3.2.0. (Remote transport is a future item; see §9.)
- Not replacing `check_triggers` (keyword matching) — `recommend_skills` is the semantic layer that complements it.
- Not redesigning the skill format or runbooks.
- Not touching the legacy `export`/`install` adapter pipeline beyond clearly disambiguating it (see §4.1).

---

## 3. Current architecture (reference for implementer)

```
React SPA (web/)  ←→  FastAPI REST (server.py)
                            ↓
CLI (openskills.py)  ──→  core.py (shared logic)  ←──  MCP Server (mcp_server.py)
                            ↓
                  File System (skills + runbooks)
```

Relevant existing pieces the implementer must reuse, not reinvent:

| Symbol | File / location | What it does |
|---|---|---|
| `match_triggers()` | `core.py` ~L554 | Keyword-overlap match of a prompt against skill triggers; returns matching skills. Reuse as the pre-filter for recommendation. |
| `get_all_skills()` | `core.py` | Returns all skills (local + global, local shadows global). Source of the candidate set. |
| `parse_frontmatter()` | `core.py` | Parses YAML frontmatter (name, description, triggers, boundaries, required_tools, etc.). |
| `call_llm_completion()` | `openskills.py` ~L361 | OpenRouter completions call (DeepSeek V4 Flash default). Reuse for the recommendation LLM call. |
| `get_api_key()` | `openskills.py` ~L338 | Resolves `OPENROUTER_API_KEY` from env / `.env`. |
| `check_triggers` (MCP tool), `list_skills`, `get_skill` | `mcp_server.py` ~L130–212 | Existing MCP tools. |
| `open-skills-context` (MCP prompt) | `mcp_server.py` ~L86 | Injects skills/context into the agent system prompt. This is the hook insertion point for Feature 1. |
| `ADAPTERS` map | `openskills.py` ~L571 | hermes, claude-code, cursor, codex, generic — used by the **legacy** adapter exporter. See §4.1. |
| `cmd_install` (legacy) | `openskills.py` ~L650 | **Legacy** static-adapter export. Do NOT overload this for MCP registration (see §4.1). |

Extraction config precedent (mirror this pattern for Feature 1):

| Env var | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Required for LLM calls. |
| `EXTRACT_MODEL` | `deepseek/deepseek-v4-flash` | Model for extraction. |
| `EXTRACT_API_BASE` | `https://openrouter.ai/api/v1/chat/completions` | Completions endpoint. |

---

## 4. Feature 1 — Semantic skill recommendation

### 4.1 Disambiguation (read first)

There is already a `cmd_install` / `export` "legacy adapter" path that writes platform-specific **static markdown** adapter files using the `ADAPTERS` map. That is the *old* "copy skill text into each platform's format" model and is the thing this whole effort is moving away from.

**Do not extend the legacy `install`/`export` for MCP work.** Feature 2 introduces a separate, clearly-named command (`connect`). Mark the legacy `install` as deprecated in `--help` text (no removal in this release).

### 4.2 Overview

Add a recommendation capability that, given a task description, returns a ranked list of the most relevant skills. It runs in two stages to keep cost and latency low:

1. **Deterministic pre-filter** — call `match_triggers()` (+ a lightweight substring/keyword pass over `name` + `description`) to reduce the candidate set from ~92 to a shortlist (cap configurable, default top 20). If the pre-filter yields fewer than `RECOMMEND_MIN_CANDIDATES` (default 3), fall back to passing all skills.
2. **LLM ranking** — send the task + the shortlist's compact metadata (name, description, triggers) to a cheap model via `call_llm_completion()`. The model returns a ranked JSON array with relevance scores and one-line rationales.

Latency tolerance: synchronous, up to ~2s is acceptable (confirmed by product owner). Every recommendation call is logged (see §4.7).

### 4.3 Core function

Add to `core.py`:

```python
def recommend_skills(
    query: str,
    *,
    scope: str = "all",          # "all" | "local" | "global"
    limit: int = 5,              # number of ranked results to return
    candidate_cap: int = 20,     # max skills sent to the LLM after pre-filter
    llm_call=None,               # injectable callable for testability; defaults to OpenRouter
) -> dict:
    """
    Rank skills by relevance to `query`.

    Pipeline:
      1. candidates = prefilter(query, get_all_skills(scope), candidate_cap)
      2. if no API key OR llm unavailable -> return prefilter order (degraded mode, llm_used=False)
      3. ranked = llm_rank(query, candidates) -> parse strict JSON
      4. return top `limit`

    Returns:
      {
        "query": str,
        "llm_used": bool,
        "model": str | None,
        "results": [
          {
            "name": str,
            "scope": "local" | "global",
            "score": float,        # 0.0–1.0
            "reason": str,         # one line, <= ~140 chars
            "triggers": [str],
          },
          ...
        ],
        "candidate_count": int,
        "elapsed_ms": int,
      }
    """
```

Design notes:
- The LLM call must be **dependency-injectable** (`llm_call` param) so unit tests run offline. Default wires to `call_llm_completion()`.
- **Degraded mode is mandatory:** if `OPENROUTER_API_KEY` is missing or the LLM call fails/times out, return the deterministic pre-filter ordering with `llm_used: false`. The tool must never hard-fail; recommendation degrades to keyword ranking.
- Keep the metadata sent to the LLM compact — name, description, and triggers only. Never send full skill bodies (cost + the agent will fetch the body via `get_skill` after choosing).

### 4.4 LLM prompt contract

System prompt (server-controlled, in `core.py`):

> You are a skill-routing classifier for an AI agent. Given a task and a list of candidate skills (each with a name, description, and triggers), return ONLY a JSON array ranking the most relevant skills for the task. Each element: `{"name": <exact skill name>, "score": <0.0–1.0 relevance>, "reason": <one short sentence>}`. Return at most N items, highest score first. No prose, no markdown, no code fences.

Parsing: strip code fences if present, `json.loads`, validate each `name` exists in the candidate set (drop hallucinated names), clamp `score` to `[0,1]`. On parse failure, log and fall back to degraded mode.

### 4.5 New env vars (mirror extraction pattern)

| Env var | Default | Purpose |
|---|---|---|
| `RECOMMEND_MODEL` | value of `EXTRACT_MODEL` or `deepseek/deepseek-v4-flash` | Model for recommendation. |
| `RECOMMEND_API_BASE` | same as `EXTRACT_API_BASE` | Completions endpoint. |
| `RECOMMEND_CANDIDATE_CAP` | `20` | Pre-filter shortlist size. |
| `RECOMMEND_TIMEOUT_MS` | `2000` | LLM timeout; on exceed → degraded mode. |

Reuse `OPENROUTER_API_KEY` / `get_api_key()`. Do not introduce a second key.

### 4.6 MCP tool

Add to `mcp_server.py` (alongside `check_triggers`, ~L130–212):

```
Tool: recommend_skills
Description: "Given a description of your current task or objective, returns a
ranked list of the most relevant Open Skills to use, with relevance scores and
short reasons. Call this BEFORE starting a task instead of listing all skills.
After choosing, call get_skill to load the full skill."
Input schema:
  {
    "query":  { "type": "string", "description": "The task or objective in natural language." },
    "limit":  { "type": "integer", "default": 5 },
    "scope":  { "type": "string", "enum": ["all","local","global"], "default": "all" }
  }
Output: text block (human-readable ranked list) + structured JSON mirroring core.recommend_skills().
```

Thin wrapper: validate args → call `core.recommend_skills()` → format. No business logic in the MCP layer.

### 4.7 REST endpoint (for parity + the web UI)

Add to `server.py`:

```
POST /api/skills/recommend
Body: { "query": str, "limit"?: int, "scope"?: "all"|"local"|"global" }
Returns: the core.recommend_skills() dict
Auth: same optional bearer-token rule as all /api routes.
```

### 4.8 The system-prompt hook (critical)

Modify the `open-skills-context` prompt resource (`mcp_server.py` ~L86) so the injected context no longer dumps all skills inline. Instead it injects a short directive plus a compact index (skill names + one-line descriptions only). Directive text (tune freely; keep it imperative):

> You have access to an Open Skills library via the `recommend_skills` tool. **Before starting any non-trivial task, call `recommend_skills` with a short description of your objective.** It returns the most relevant skills ranked by relevance. Load the chosen skill with `get_skill` and follow its procedure and verification contract. Do not attempt to enumerate the full library; use the recommender.

Add a config flag to control verbosity of the injected context:

| Env var | Default | Behavior |
|---|---|---|
| `OPENSKILLS_CONTEXT_MODE` | `index` | `index` = directive + name/description index (recommended); `full` = legacy full-dump; `directive_only` = directive, no index. |

### 4.9 Acceptance criteria — Feature 1

- [ ] `core.recommend_skills()` returns correctly shaped dict; unit-tested offline via injected `llm_call`.
- [ ] Missing API key or LLM timeout returns deterministic pre-filter results with `llm_used: false` (no exception).
- [ ] Hallucinated skill names from the LLM are dropped (validated against candidate set).
- [ ] MCP `recommend_skills` tool callable from an MCP client and returns a ranked list for a sample query.
- [ ] `POST /api/skills/recommend` returns the same ranking as the MCP tool for the same input.
- [ ] `open-skills-context` in `index` mode injects the directive + index, not a full dump; `full` mode preserves legacy behavior.
- [ ] Each recommendation logs: timestamp, query, candidate_count, llm_used, model, top result, elapsed_ms.

---

## 5. Feature 2 — Agent MCP registration (`connect` CLI command)

### 5.1 Overview

A new CLI command writes the Open Skills MCP server entry into each target agent's MCP config file, so the agent connects to the live server. Idempotent, cross-platform, dry-run-able, reversible.

> **Naming:** use `connect` (not `install`) to avoid colliding with the legacy adapter exporter (§4.1). Acceptable alternative if the owner prefers: `install --mcp`. Pick one; `connect` is the recommendation.

### 5.2 CLI surface

```bash
# Detect agents on the system and show install status
python3 openskills.py connect --list

# Register the MCP server into specific agents
python3 openskills.py connect --cursor --codex

# Register into every detected/supported agent
python3 openskills.py connect --all

# Register into an unknown/custom harness by explicit config path + format
python3 openskills.py connect --target /path/to/config.json --format mcp-json

# Preview changes without writing
python3 openskills.py connect --all --dry-run

# Remove the Open Skills entry
python3 openskills.py connect --cursor --uninstall

# Scope which skills directory the server serves (passes through to the server invocation)
python3 openskills.py connect --all --scope global
```

### 5.3 Agent registry

Define an `AGENT_REGISTRY` (new map, distinct from the legacy `ADAPTERS` map) describing each supported agent: config path per OS, config format, and the JSON key path where MCP servers live.

```python
AGENT_REGISTRY = {
  "cursor": {
    "label": "Cursor",
    "format": "mcp-json",
    "paths": {
      "darwin":  "~/.cursor/mcp.json",
      "linux":   "~/.cursor/mcp.json",
      "windows": "%USERPROFILE%\\.cursor\\mcp.json",
    },
    "servers_key": "mcpServers",     # JSON object keyed by server name
  },
  "claude-code": {
    "label": "Claude Code",
    "format": "mcp-json",
    "paths": { ... },               # implementer: resolve current Claude Code MCP config location per OS
    "servers_key": "mcpServers",
  },
  "devin": {
    "label": "devin",
    "format": "mcp-json",
    "paths": { ... },               # e.g. ~/.codeium/devin/mcp_config.json — VERIFY at implement time
    "servers_key": "mcpServers",
  },
  "codex": {
    "label": "Codex",
    "format": "toml-or-json",       # VERIFY current Codex MCP config format/location at implement time
    "paths": { ... },
    "servers_key": "...",
  },
  # extensibility: adding an agent = one entry here
}
```

> **Implementer note:** config paths/formats for these harnesses change. Resolve and verify the exact current path and schema for each at implementation time (search official docs); do NOT hardcode from memory. Treat the values above as placeholders. The architecture (registry-driven) is the requirement; the exact paths are data.

### 5.4 The entry that gets written

For a standard `mcp-json` agent, merge (do not clobber sibling servers) an entry like:

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "python3",
      "args": ["/abs/path/to/openskills.py", "mcp", "start", "--scope", "all"],
      "env": {}
    }
  }
}
```

The command resolves the absolute path to the current `openskills.py` (or the installed console-script entry point if packaged). `--scope` reflects the `--scope` flag.

### 5.5 Behavioral requirements

- **Idempotent:** running twice produces no duplicate entries; an existing `open-skills` entry is updated in place.
- **Non-destructive merge:** preserve all other servers and unrelated keys in the file. Never rewrite the whole file from a template.
- **Backup:** before first write to any file, copy it to `<file>.bak-<timestamp>`.
- **Create-if-missing:** if the config file/dir doesn't exist but the agent is "known," create it with a minimal valid structure (only when the user explicitly targeted that agent, not under `--all` auto-detect unless detected).
- **Dry-run:** `--dry-run` prints a unified diff of intended changes and writes nothing.
- **Detection:** an agent is "detected" if its config dir/file exists. `--list` shows: agent label, detected (y/n), open-skills entry present (y/n), config path.
- **Format adapters:** `mcp-json` is the primary writer. Implement a small writer-interface so non-JSON formats (e.g. TOML) can be added without touching the command flow.
- **Validation after write:** re-read and parse the file to confirm it's still valid JSON/TOML; if parsing fails, restore from backup and error out.

### 5.6 Telemetry / output

Human-readable summary table at the end: per agent → action taken (installed / updated / skipped / uninstalled / failed) + path. Non-zero exit if any targeted agent failed.

### 5.7 Acceptance criteria — Feature 2

- [ ] `connect --list` reports detection + entry-present status for all registry agents.
- [ ] `connect --cursor` writes a valid `open-skills` MCP entry merged into existing `mcp.json` without disturbing other servers.
- [ ] Re-running is idempotent (no duplicates; in-place update).
- [ ] A timestamped `.bak` is created before the first write to any file.
- [ ] `--dry-run` prints a diff and writes nothing.
- [ ] `--target ... --format mcp-json` registers into an arbitrary path.
- [ ] `--uninstall` removes only the `open-skills` entry, leaving siblings intact.
- [ ] Cross-platform path resolution works on macOS/Linux/Windows (unit-test path resolution with mocked `platform.system()` and `$HOME`/`%USERPROFILE%`).
- [ ] Invalid write is detected and rolled back from backup.
- [ ] Legacy `install`/`export` `--help` text marks it deprecated and points to `connect`.

---

## 6. Feature 3 — Web "Agent Setup" page

### 6.1 Overview

A new SPA page (under a nav item, e.g. **Agent Setup** or under Settings) that visualizes agent detection/install status and lets the user install/uninstall and target unknown harnesses manually — the safety valve for harnesses the CLI doesn't auto-detect.

### 6.2 Backend endpoints (`server.py`)

```
GET  /api/agents
  -> [ { "id","label","detected":bool,"installed":bool,"configPath":str,"format":str }, ... ]
     (server-side equivalent of `connect --list`)

POST /api/agents/{id}/connect
  Body: { "scope"?: "all"|"local"|"global", "dryRun"?: bool }
  -> { "action": "installed|updated|skipped|failed", "path": str, "diff"?: str }

POST /api/agents/{id}/disconnect
  -> { "action": "uninstalled|skipped|failed", "path": str }

POST /api/agents/custom/connect
  Body: { "configPath": str, "format": "mcp-json"|..., "scope"?: ... , "dryRun"?: bool }
  -> same shape as connect
```

All endpoints share core registration logic with the CLI (extract a `core`-level or shared module function so CLI and REST don't duplicate the merge/backup/validate logic). Respect optional bearer auth.

### 6.3 UI requirements

- **Detected agents list:** card/row per agent → label, detected badge, "Open Skills installed" badge, config path, and a primary action button (Connect / Reconnect / Disconnect).
- **Dry-run preview:** before writing, optionally show the diff returned by the endpoint in a modal; confirm to apply.
- **Manual target (unknown harness):** a form with config-path input + format select + scope select + "Test path" (validates the path is writable / parseable) and a Connect button hitting `/api/agents/custom/connect`.
- **Status feedback:** success/error toasts (reuse existing `useToast()`); reflect new install state without full reload (TanStack Query invalidation on `["agents"]`).
- **Empty/none-detected state:** explanatory copy + pointer to the manual-target form.
- **Safety:** the page never asks for or stores secrets/tokens. Path entry only.

Follow existing stack conventions: React 19 + React Router 7 + TanStack Query 5 + Tailwind CSS 4. Match the existing Skills/Runbooks page patterns (query hooks, layout, components).

### 6.4 Acceptance criteria — Feature 3

- [ ] `GET /api/agents` returns detection/install status matching `connect --list`.
- [ ] Page lists detected agents with correct badges and config paths.
- [ ] Connect/Disconnect buttons call the endpoints and update state without page reload.
- [ ] Dry-run preview shows a diff before applying.
- [ ] Manual-target form installs into an arbitrary valid path and surfaces errors clearly for bad paths.
- [ ] No secret/token input anywhere on the page.
- [ ] CLI and REST share the same underlying registration logic (no duplicated merge/backup code).

---

## 7. Cross-cutting requirements

- **Shared logic in `core.py`:** recommendation ranking and the agent-registration merge/backup/validate logic must live in shared modules so CLI, MCP server, and REST all call the same code. `mcp_server.py` and `server.py` stay thin.
- **Degraded-mode everywhere:** no feature may hard-fail on a missing `OPENROUTER_API_KEY`. Recommendation degrades to keyword ranking; registration/UI are unaffected by LLM availability.
- **Idempotency & reversibility:** all file-mutating operations (config writes) are idempotent and reversible (backups).
- **Logging:** structured log line per recommendation and per registration action.
- **Docs:** update `README.md` (new `recommend_skills` tool, `connect` command, Agent Setup page, new env vars) and the docs site. Add the `recommend_skills` tool and the new endpoints to the MCP/REST tables.
- **Privacy:** queries sent to the LLM contain task text + skill metadata only — never file contents, never credentials. State this in README.

---

## 8. Testing summary

| Layer | Tests |
|---|---|
| `core.recommend_skills` | Offline (injected `llm_call`): ranking shape, degraded mode, hallucination drop, score clamp, candidate cap, scope filter. |
| `core` registration | Path resolution per OS (mocked), idempotent merge, sibling preservation, backup creation, rollback on invalid write, uninstall. |
| MCP tool | `recommend_skills` returns ranked list end-to-end against a stub server. |
| REST | `/api/skills/recommend`, `/api/agents*` happy-path + auth + error cases. |
| Web | (Project has no frontend test suite yet — at minimum, manual QA checklist for the Agent Setup page; add component tests if introducing a runner.) |

A QA artifact (screenshots desktop + mobile of the Agent Setup page, console showing zero uncaught errors) should be produced per the project's existing verification convention.

---

## 9. Sequencing & rollout

1. **Feature 1 first** — it's the value core and is independent. Land `core.recommend_skills`, the MCP tool, the REST endpoint, the context-hook change, env vars, tests, docs.
2. **Feature 2 second** — depends on the MCP server existing (it does) and on having something worth connecting to (Feature 1). Land `connect` + `AGENT_REGISTRY` + shared registration logic.
3. **Feature 3 third** — depends on Feature 2's shared registration logic and `/api/agents*` endpoints.

Ship as **v3.2.0**.

---

## 10. Open questions

- **Command name:** `connect` (recommended) vs `install --mcp`. Confirm before building Feature 2.
- **Context default mode:** default `OPENSKILLS_CONTEXT_MODE=index` assumes the index is cheaper than a full dump while still aiding the agent. Confirm `index` over `directive_only`.
- **Codex/devin config formats:** must be verified against current official docs at implementation time — flagged as data, not architecture.
- **Remote MCP server:** out of scope here, but the `connect` registry should be designed so a future remote-URL transport is an additive entry shape, not a rewrite.
