# Graph Report - .  (2026-06-21)

## Corpus Check
- Corpus is ~22,070 words - fits in a single context window. You may not need a graph.

## Summary
- 184 nodes · 262 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Skill Spec & Adapters|Skill Spec & Adapters]]
- [[_COMMUNITY_CLI Commands|CLI Commands]]
- [[_COMMUNITY_MCP Server|MCP Server]]
- [[_COMMUNITY_Claude Code Tests|Claude Code Tests]]
- [[_COMMUNITY_Codex Tests|Codex Tests]]
- [[_COMMUNITY_Cursor Tests|Cursor Tests]]
- [[_COMMUNITY_Generic Tests|Generic Tests]]
- [[_COMMUNITY_Hermes Tests|Hermes Tests]]
- [[_COMMUNITY_Core Skill Tests|Core Skill Tests]]
- [[_COMMUNITY_Platform Export|Platform Export]]
- [[_COMMUNITY_Skill Scoping|Skill Scoping]]

## God Nodes (most connected - your core abstractions)
1. `die()` - 13 edges
2. `cmd_extract()` - 9 edges
3. `ok()` - 8 edges
4. `cmd_runbook()` - 8 edges
5. `parse_frontmatter() Helper` - 8 edges
6. `get_local_dir()` - 7 edges
7. `Support Billing Recovery Skill` - 7 edges
8. `get_global_dir()` - 6 edges
9. `parse_frontmatter()` - 6 edges
10. `cmd_install()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Work Package Checklist (8 Ownership Checks)` --conceptually_related_to--> `cmd_score() (One-Question Test CLI)`  [INFERRED]
  SPEC.md → openskills.py
- `AI Chat Frontend Design Skill (Pending Review)` --references--> `Session-to-Skill Extractor (Flywheel)`  [INFERRED]
  .open-skills/skills/pending-review/ai-chat-frontend-design/skill.md → openskills.py
- `MCP Tool: check_triggers` --semantically_similar_to--> `cmd_validate() (Anatomy Validator CLI)`  [INFERRED] [semantically similar]
  mcp_server.py → openskills.py
- `MCP Tool: advance_runbook` --semantically_similar_to--> `cmd_runbook() (Runbook State Machine CLI)`  [INFERRED] [semantically similar]
  mcp_server.py → openskills.py
- `cmd_validate() (Anatomy Validator CLI)` --implements--> `skill.md File Format (YAML Frontmatter + Markdown Body)`  [EXTRACTED]
  openskills.py → SPEC.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Platform Adapter Export System** — adapters_dict, cmd_export_fn, adapter_claude_code, adapter_codex, adapter_hermes, adapter_generic, platform_adapters_concept [EXTRACTED 0.95]
- **Skill Anatomy Specification and Validation Pipeline** — skill_md_format, cmd_validate_fn, work_package_checklist, cmd_score_fn, support_billing_recovery_tests [INFERRED 0.85]
- **Runbook Execution Flow (CLI + MCP)** — runbook_concept, cmd_runbook_fn, mcp_tool_advance_runbook, release_day_runbook, mcp_prompt_context [INFERRED 0.80]

## Communities (11 total, 1 thin omitted)

### Community 0 - "Skill Spec & Adapters"
Cohesion: 0.09
Nodes (29): Claude Code Adapter for Support Billing Recovery, Codex Adapter for Support Billing Recovery, Generic Adapter for Support Billing Recovery, Hermes Adapter for Support Billing Recovery, AI Chat Frontend Design Skill (Pending Review), cmd_runbook() (Runbook State Machine CLI), cmd_score() (One-Question Test CLI), cmd_validate() (Anatomy Validator CLI) (+21 more)

### Community 1 - "CLI Commands"
Cohesion: 0.20
Nodes (27): call_openai_chat_completions(), cmd_export(), cmd_extract(), cmd_graph(), cmd_init(), cmd_install(), cmd_list(), cmd_mcp() (+19 more)

### Community 2 - "MCP Server"
Cohesion: 0.08
Nodes (24): FastMCP Framework, advance_runbook(), check_triggers(), get_global_runbook_resource(), get_global_skill_resource(), get_local_runbook_resource(), get_local_skill_resource(), get_runbook_state() (+16 more)

### Community 3 - "Claude Code Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 4 - "Codex Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 5 - "Cursor Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 6 - "Generic Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 7 - "Hermes Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 8 - "Core Skill Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 9 - "Platform Export"
Cohesion: 0.50
Nodes (4): ADAPTERS Dictionary (Platform Wrappers), cmd_export() (Platform Export CLI), Platform Adapters (Generated Wrappers), Rationale: Platform-Agnostic Core with Generated Adapters

## Knowledge Gaps
- **16 isolated node(s):** `Open Skills CLI (openskills.py)`, `manifest.yaml Declaration Format`, `Local Scope (.open-skills/ Directory)`, `Global Scope (~/.config/open-skills/ Directory)`, `Claude Code Adapter for Support Billing Recovery` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `parse_frontmatter() Helper` connect `Skill Spec & Adapters` to `Platform Export`, `MCP Server`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **What connects `Read a local skill's markdown content.`, `Read a global skill's markdown content.`, `Read a local runbook's content.` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Skill Spec & Adapters` be split into smaller, more focused modules?**
  _Cohesion score 0.08620689655172414 - nodes in this community are weakly interconnected._
- **Should `MCP Server` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._