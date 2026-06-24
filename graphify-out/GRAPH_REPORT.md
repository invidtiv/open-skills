# Graph Report - .  (2026-06-24)

## Corpus Check
- Corpus is ~31,914 words - fits in a single context window. You may not need a graph.

## Summary
- 476 nodes · 742 edges · 31 communities (19 shown, 12 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.81)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_React UI Components|React UI Components]]
- [[_COMMUNITY_Core Library|Core Library]]
- [[_COMMUNITY_Backend Services & API|Backend Services & API]]
- [[_COMMUNITY_Core Unit Tests|Core Unit Tests]]
- [[_COMMUNITY_MCP Server Tools|MCP Server Tools]]
- [[_COMMUNITY_Web Package Dependencies|Web Package Dependencies]]
- [[_COMMUNITY_Runbook State Machine|Runbook State Machine]]
- [[_COMMUNITY_App TypeScript Config|App TypeScript Config]]
- [[_COMMUNITY_Node TypeScript Config|Node TypeScript Config]]
- [[_COMMUNITY_Claude Code Adapter Tests|Claude Code Adapter Tests]]
- [[_COMMUNITY_Codex Adapter Tests|Codex Adapter Tests]]
- [[_COMMUNITY_Cursor Adapter Tests|Cursor Adapter Tests]]
- [[_COMMUNITY_Generic Adapter Tests|Generic Adapter Tests]]
- [[_COMMUNITY_Hermes Adapter Tests|Hermes Adapter Tests]]
- [[_COMMUNITY_Billing Recovery Tests|Billing Recovery Tests]]
- [[_COMMUNITY_Frontmatter Form|Frontmatter Form]]
- [[_COMMUNITY_Platform Adapters|Platform Adapters]]
- [[_COMMUNITY_Skill Validation|Skill Validation]]
- [[_COMMUNITY_Spec Core Concepts|Spec Core Concepts]]
- [[_COMMUNITY_Root TS Config|Root TS Config]]
- [[_COMMUNITY_Claude Code Adapter|Claude Code Adapter]]
- [[_COMMUNITY_Codex Adapter|Codex Adapter]]
- [[_COMMUNITY_Generic Adapter|Generic Adapter]]
- [[_COMMUNITY_Hermes Adapter|Hermes Adapter]]
- [[_COMMUNITY_Docs Site|Docs Site]]
- [[_COMMUNITY_MCP Resources|MCP Resources]]
- [[_COMMUNITY_Legacy CLI Commands|Legacy CLI Commands]]
- [[_COMMUNITY_Package Metadata|Package Metadata]]
- [[_COMMUNITY_Project README|Project README]]

## God Nodes (most connected - your core abstractions)
1. `request()` - 22 edges
2. `compilerOptions` - 17 edges
3. `compilerOptions` - 16 edges
4. `get_all_skills()` - 13 edges
5. `die()` - 13 edges
6. `validate_skill_content()` - 11 edges
7. `get_local_dir()` - 11 edges
8. `parse_frontmatter()` - 11 edges
9. `useToast()` - 11 edges
10. `resolve_skill()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Runbooks as Composition` --references--> `Runbook State Machine (start/advance/prev/reset)`  [INFERRED]
  README.md → core.py
- `validate_skill_content()` --implements--> `Open Skill Package Format`  [EXTRACTED]
  core.py → SPEC.md
- `ValidationPanel Component` --shares_data_with--> `validate_skill_content()`  [INFERRED]
  web/src/components/ValidationPanel.tsx → core.py
- `import_github()` --semantically_similar_to--> `openskills.py (CLI Entry Point)`  [INFERRED] [semantically similar]
  server.py → openskills.py
- `FrontmatterForm Component` --implements--> `Open Skill Package Format`  [INFERRED]
  web/src/components/FrontmatterForm.tsx → SPEC.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Core Module As Shared Logic Hub** — core_module, server_module, mcp_server_module, openskills_cli [EXTRACTED 1.00]
- **LLM-Powered Skill Extraction Pipeline** — openskills_extract_command, openskills_get_last_session, openskills_call_llm, concept_openrouter, concept_deepseek_v4_flash, concept_superpowers_db, concept_claude_history [EXTRACTED 0.95]
- **Web UI Skill Editing Flow** — web_skill_detail_page, web_frontmatter_form, web_validation_panel, web_file_tree, web_api_client, server_skills_endpoints [EXTRACTED 0.90]

## Communities (31 total, 12 thin omitted)

### Community 0 - "React UI Components"
Cohesion: 0.06
Nodes (53): FileTree(), Props, Layout(), NAV, Props, RunbookTracker(), Props, Toast (+45 more)

### Community 1 - "Core Library"
Cohesion: 0.09
Nodes (64): Any, advance_runbook(), find_skill_file(), get_all_skills(), get_global_dir(), get_local_dir(), get_runbook_state_file(), match_triggers() (+56 more)

### Community 2 - "Backend Services & API"
Cohesion: 0.05
Nodes (52): BaseModel, Claude History JSONL (Chat Log Source), DeepSeek V4 Flash Model, FastMCP Library, OpenRouter API (External LLM Service), Superpowers SQLite DB (Chat Log Source), core.py Module (Shared Logic), mcp_server.py (MCP Server) (+44 more)

### Community 4 - "MCP Server Tools"
Cohesion: 0.07
Nodes (29): advance_runbook(), check_triggers(), get_global_runbook_resource(), get_global_skill_resource(), get_local_runbook_resource(), get_local_skill_resource(), get_runbook_state(), get_runbook_state_resource() (+21 more)

### Community 5 - "Web Package Dependencies"
Cohesion: 0.07
Nodes (29): dependencies, react, react-dom, react-router-dom, @tanstack/react-query, devDependencies, eslint, @eslint/js (+21 more)

### Community 6 - "Runbook State Machine"
Cohesion: 0.10
Nodes (20): _write_state_atomic() Atomic File Write, Runbook State Machine (start/advance/prev/reset), Extracting Workflows (The Flywheel), Runbooks as Composition, Runbook REST API Endpoints, Rationale: Portability Via Vendor-Agnostic Format, Open Skill Package Format, api.ts (Frontend API Client) (+12 more)

### Community 7 - "App TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 8 - "Node TypeScript Config"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 9 - "Claude Code Adapter Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 10 - "Codex Adapter Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 11 - "Cursor Adapter Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 12 - "Generic Adapter Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 13 - "Hermes Adapter Tests"
Cohesion: 0.17
Nodes (10): main(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_compatibility_declared(), test_decision_logic(), test_manifest_dependencies_declared(), test_manifest_exists(), test_permissions_bounded() (+2 more)

### Community 14 - "Billing Recovery Tests"
Cohesion: 0.15
Nodes (6): main(), test_decision_logic(), test_platform_agnostic(), The core SKILL.md must not contain platform-specific markers., Verify the decision logic in Step 3 is well-defined., test_verification_contract_section_exists()

### Community 16 - "Platform Adapters"
Cohesion: 0.67
Nodes (3): ADAPTERS Map (hermes, claude-code, cursor, codex, generic), Platform Adapters, Rationale: Adapters Are Generated Not Maintained

### Community 17 - "Skill Validation"
Cohesion: 0.67
Nodes (3): CHECKS List (One-Question Test Implementation), One-Question Test, Work Package Checklist (8 Checks)

### Community 18 - "Spec Core Concepts"
Cohesion: 0.67
Nodes (3): Open Skill Concept, Rationale: Skill Ownership Over Vendor Lock-in, Skill Debt Concept

## Knowledge Gaps
- **105 isolated node(s):** `openskills`, `Request`, `name`, `private`, `version` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `validate_skill_content()` connect `Core Library` to `Runbook State Machine`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `ValidationPanel Component` connect `Runbook State Machine` to `Core Library`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **What connects `core — shared logic for Open Skills CLI and MCP server.  Fixes addressed:   S1`, `Slugify a skill name. Raises ValueError if result is empty.`, `Validate skill markdown content. Returns dict with 'errors', 'checks', and 'warn` to the rest of the system?**
  _156 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `React UI Components` be split into smaller, more focused modules?**
  _Cohesion score 0.056842105263157895 - nodes in this community are weakly interconnected._
- **Should `Core Library` be split into smaller, more focused modules?**
  _Cohesion score 0.08997668997668998 - nodes in this community are weakly interconnected._
- **Should `Backend Services & API` be split into smaller, more focused modules?**
  _Cohesion score 0.054098360655737705 - nodes in this community are weakly interconnected._
- **Should `Core Unit Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._