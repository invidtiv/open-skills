---
name: implement-nothing-ui-frontend
description: Design and implement a Nothing-inspired admin/operator frontend for a FastAPI backend, following a strict monochrome typographic design system with Space Grotesk/Mono/Doto fonts, three-layer hierarchy, and locked architectural rules.
triggers:
  - "User requests frontend design or implementation for a FastAPI admin/operator UI"
  - "User asks to apply the Nothing design system to a web frontend"
  - "User needs to build a React SPA that mounts under a FastAPI backend"
boundaries:
  - "Do not modify backend Python code unless explicitly requested"
  - "Do not use Next.js, Vercel, or SSR frameworks — the SPA must be a static build served by FastAPI"
  - "Do not add shadows, gradients, toast popups, skeleton loaders, or zebra striping"
  - "Do not use color for decoration — only for data status values (success green, warning amber, error red)"
  - "Do not collapse /events, /logs, and /audit into a single timeline — they must remain separate UI surfaces"
  - "Do not implement DELETE on rooms — use archive semantics instead"
  - "Do not use port 5173 for dev — pick an unused port with strictPort: true"
required_tools:
  - Vite
  - React 18
  - TypeScript
  - Tailwind CSS
  - TanStack Query v5
  - react-router-dom v6
  - Google Fonts (Space Grotesk, Space Mono, Doto)
  - EventSource (for SSE)
output_format: "A fully functional static SPA in a web/ directory, with a design spec document at docs/frontend-design.md, and a build pipeline that emits to app/static/admin/ for FastAPI serving"
---

## Objective
Design and implement a complete admin/operator frontend for a FastAPI-based approval-gated multi-agent chat gateway, using the Nothing design system. The frontend must be a Vite + React 18 + TypeScript SPA that mounts under FastAPI at /admin, with no backend changes required for auth (uses X-Admin-API-Key header or ?admin_api_key= query param for SSE).

## Procedure
1. **Explore the repo** — Read README.md, tasks.md, docs/, and app/ to understand the backend capabilities, locked architectural rules, and existing endpoints.
2. **Design the frontend spec** — Write docs/frontend-design.md covering:
   - Information architecture (Dashboard, Agents, Rooms, Sessions, Live Feed, Logs, Audit, Subscriptions, Integrations, Settings)
   - Core user flows (approve agent, create room, assign agent, move session, archive room, investigate delivery failure)
   - Component tree with a single event-taxonomy.ts mirroring the canonical event vocabulary
   - Nothing visual direction: Space Grotesk + Space Mono + Doto fonts, three-layer hierarchy, OLED-black dark mode, monochrome canvas with status colors only on data values, spacing as hierarchy, no dividers by default, inline status text instead of toasts, one deliberate break per screen
   - Anti-patterns list (no gradients, shadows, skeleton loaders, toast popups, zebra striping, filled icons, emoji as UI, parallax, bounce easing)
   - Contract-alignment checklist enforcing locked rules (event immutability, contract separation, explicit subscription scopes, explicit room archive)
   - 3-pass phasing plan
3. **Set up the web project** — Create web/ with Vite + React 18 + TypeScript + Tailwind, configure Nothing token layer in tailwind.config.js (canvas, surface, ink, line, ok, warn, err colors; fontFamily sans/mono/display), load Google Fonts in index.html, set class="dark" on html.
4. **Build the API client** — Create web/src/api/ with:
   - client.ts: fetch wrapper with ApiError class, attaches X-Admin-API-Key header from sessionStorage; streamEvents() returns EventSource pointing to /admin/events/stream with ?admin_api_key= query param
   - types.ts: Agent, Room, SessionT, EventT, EventLog, AuditLog, Subscription, SubscriptionScope, SubscriptionStatus, DeliveryTestResponse, AuthorizationEvent
   - endpoints.ts: All endpoint functions for agents, rooms, sessions, events, logs, audit, subscriptions, integrations
5. **Build layout components** — AppShell with grouped nav (Dashboard, Agents with pending badge, Rooms, Sessions, // OBSERVABILITY: Live/Logs/Audit, // INTEGRATIONS: Subscriptions/Channels, // SYSTEM: Settings), SideNav, ApiKeyGate, PageHeader, StatusBadge, DataTable
6. **Build domain components** — MoveSessionDialog, ArchiveRoomDialog, DeliveryHealth, AgentHistoryDrawer
7. **Build route pages** — Dashboard (Doto hero of pending count, 3-column grid), Agents (tabs + inline approve/reject/revoke + history drawer), Rooms + RoomDetail (create dialog, agent assignment, sessions list, archive dialog), Sessions + SessionDetail (event timeline with live SSE stream, operator compose box, move dialog), LiveFeed (pause/resume SSE tail), Logs (filtered query), Audit (flat ledger), Subscriptions (list with scope/status filters, inline enable/disable, test action), Integrations (Claude MCP pane + OpenClaw pane), Settings (clear key, exposure notes)
8. **Wire into FastAPI** — Add _mount_admin_ui() helper in app/main.py that serves /admin/assets/* via StaticFiles and /admin/{path} with SPA fallback to index.html
9. **Configure Vite** — Set base: "/admin/", outDir: "../app/static/admin", DEV_PORT to an unused port (not 5173) with strictPort: true, proxy for all API paths to the gateway
10. **Build and verify** — Run npm run build, boot the gateway, verify GET /admin → 200, GET /admin/assets/* → 200, GET /admin/{client-route} → 200 (SPA fallback), GET /health → 200
11. **Add filters to list pages** — Sessions: room picker + status segmented control; Logs: six-field filter grid (type, category, origin, actor_id, room_id, session_id); Audit: five-field filter grid (action, actor_id, agent_id, room_id, session_id)
12. **Add missing tabs** — SessionDetail: Context, Transfers, Logs tabs; RoomDetail: Logs tab + room edit (PATCH)
13. **Add subscription create dialog** — With explicit scope radio (global/room/session) per locked checklist
14. **Commit and push** — Clean stray compiled .js files, update .gitignore, commit with descriptive message, push to origin/main

## Verification Contract (NON-NEGOTIABLE)
Your job is NOT done until you provide:
- [ ] A complete design spec at docs/frontend-design.md covering IA, screens, flows, component tree, Nothing visual direction, anti-patterns, contract-alignment checklist, and phasing
- [ ] A fully functional Vite + React 18 + TypeScript SPA in web/ that builds cleanly (npm run build passes)
- [ ] The SPA mounts under FastAPI at /admin with SPA fallback for client-side routes
- [ ] All core pages render: Dashboard, Agents, Rooms, RoomDetail, Sessions, SessionDetail, LiveFeed, Logs, Audit, Subscriptions, Integrations, Settings
- [ ] Session move dialog and room archive dialog are implemented and wired
- [ ] Delivery-health widget renders on the Dashboard
- [ ] Claude MCP pane and OpenClaw pane render on the Integrations page
- [ ] Filters work on Sessions, Logs, and Audit pages
- [ ] SessionDetail has Context, Transfers, and Logs tabs
- [ ] Subscription create dialog exists with explicit scope radio
- [ ] End-to-end serving verified: GET /admin → 200, GET /admin/assets/* → 200, GET /admin/{client-route} → 200, GET /health → 200
- [ ] All code is committed and pushed to origin/main
