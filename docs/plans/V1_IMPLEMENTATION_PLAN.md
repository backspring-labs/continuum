# Continuum V1 Implementation Plan

**Date:** 2026-02-03
**Status:** Draft (v0.9)
**Reference:** `CONTINUUM_V1_ARCH_SPEC.md`, `CONTINUUM_INTENT_DOC.md`

---

## Overview

This plan breaks down the V1 implementation into five milestones (M0–M4), each building on the previous. The goal is to deliver a functional control-plane UI shell that can host plugins, render contributions into regions, and execute commands with proper guardrails.

**Switchboard dependency:** Continuum requires Switchboard (PatchPanel) as its extensibility substrate. Ensure Switchboard is available before starting M1.

**Key principle:** Host contracts are frozen early (M0/M1) so that M2–M4 build on stable foundations without schema churn.

---

## Scope Guard

Continuum is a **shell + adapters**; domain logic stays in target systems.

- Prefer embedding/linking to existing tools (Grafana, etc.) rather than rebuilding observability
- Continuum hosts operational surfaces; it does not own orchestration, identity, or business logic
- When in doubt, keep it out of V1

**V1 Execution Context:**
- Continuum runs standalone with sample plugins
- Plugin discovery: `./plugins/` directory (hardcoded, no configuration)
- Shell title: "Continuum Builder" (hardcoded)
- Single command: `continuum run` starts API server + serves shell
- Host app integration (configurable plugins_dir, branding, embedding) deferred to V2

---

## Tech Stack Decisions

### Chosen Stack (V1)

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Backend** | Python 3.11+ / FastAPI | Typed, async, auto-generates OpenAPI spec as API contract |
| **Web Shell** | SvelteKit + TypeScript | Compiles to efficient vanilla JS, first-class Web Component support |
| **Plugin Format** | Web Components | Framework-agnostic — any framework can compile to this standard |
| **iOS (V1)** | Capacitor | WebView wrapper with native shell, ships fast |
| **iOS (Future)** | SwiftUI shell + WebView panels | Native chrome, plugin panels remain web-based |
| **Styling** | CSS Custom Properties | Design tokens shared across web and native themes |
| **API Contract** | OpenAPI (generated from FastAPI) | Versioned, typed, enables future shell implementations |

### Plugin Format (V1) — Svelte Only

Plugins MUST compile to Web Components using Svelte's `customElement` feature. **V1 enforces Svelte-only builds.**

**V1 enforcement:**
- Plugins MUST ship WC bundles produced by Svelte `customElement` build
- No other framework builds are supported, tested, or guaranteed to work
- Build toolchain: Svelte + Vite (standardized in plugin template)
- Contract tests validate Svelte WC outputs only

**V1 scope:**
- Svelte plugins compiled to Web Components ✓
- Single framework, single compilation path, single build toolchain
- Cross-framework portability is explicitly out of scope for V1

**Future (not V1):**
- `@continuum/plugin-sdk-react` — React → WC compilation helpers
- `@continuum/plugin-sdk-core` — Framework-agnostic types
- Cross-framework portability testing and guarantees

### Future Shell Variants (not V1, but architecture supports)

- `continuum-shell-react` — For teams/orgs preferring React
- `continuum-shell-native-ios` — SwiftUI consuming API directly, WebView for plugin panels
- `continuum-shell-native-android` — Kotlin/Jetpack Compose equivalent

### V2 and Beyond (Deferred)

**Host App Integration:**
V1 runs Continuum standalone with sample plugins. V2 will add:
- Configurable `plugins_dir` (host app points to its own plugins folder)
- `continuum.toml` configuration file for host app customization
- Custom branding / theming (title, logo, colors)
- Multiple plugin directories (merge host plugins + shared plugins)
- Embedding modes (Continuum as library vs standalone service)

```
# Future V2 config example
[continuum]
plugins_dir = "./my_app_plugins"
title = "SquadOps Control Plane"
theme = "./theme/squadops-tokens.css"
```

**Runtime Plugin Loading:**
V1 uses compile-time bundling. V2 may add:
- Dynamic Web Component loading via `ComponentLoader` interface
- Remote plugin bundles (fetch from URL)
- Plugin hot-reload for development

### Future Features (not V1, documented for planning)

**Perspective-Scoped Navigation:**
Currently, `ui.slot.left_nav` shows the same items regardless of active perspective. A future enhancement:
- Add `perspective_scope` to `NavContribution` (same pattern as `PanelContribution`)
- Left nav would show: global nav items + perspective-specific nav items
- Enables context-sensitive tooling per perspective (e.g., Signal shows signal-specific actions, Systems shows admin tools)
- Consider: nested nav groups, collapsible sections, perspective "workspaces"

```
Left Nav (Signal perspective):        Left Nav (Systems perspective):
┌──────────────┐                      ┌──────────────┐
│ [Perspectives - always visible]    │ [Perspectives - always visible]
│  ● Signal                          │  ○ Signal
│  ○ Research                        │  ○ Research
│  ○ Systems                         │  ● Systems
├──────────────┤                      ├──────────────┤
│ [Signal Tools - scoped]            │ [Admin Tools - scoped]
│  📊 Metrics                        │  🔌 Plugins
│  📈 Timeline                       │  📋 Registry
│  🔔 Alerts                         │  🩺 Diagnostics
├──────────────┤                      ├──────────────┤
│ [Actions - always visible]         │ [Actions - always visible]
│  ⌘ Commands                        │  ⌘ Commands
│  💬 Chat                           │  💬 Chat
└──────────────┘                      └──────────────┘
```

### Web Component Contract (V1)

All plugin UI MUST be compiled to Web Components via Svelte `customElement`. V1 enforces Svelte-only; no other framework builds are supported or tested.

**Tag naming (canonical pattern):**
- Plugin ID transform: `vendor.plugin_name` → `vendor-plugin-name` (dots become hyphens)
- Pattern: `{ui_tag_prefix}-{component-name}` (all kebab-case)
- Example: plugin `continuum.sample_signal` → prefix `continuum-sample-signal` → tag `<continuum-sample-signal-timeline>`
- Example: plugin `acme.dashboard` → prefix `acme-dashboard` → tag `<acme-dashboard-overview>`

**Registry stores full tag:**
- Manifest `component` field contains the complete tag string
- Registry payload includes the exact tag; UI renders it directly via `<svelte:element this={tag}>`
- No runtime transformation; what's in registry is what's rendered

**Svelte-only compliance (structural check):**
- Compliance = each declared tag is defined by its bundle via `customElements.define('{tag}', ...)`
- Build verification: grep/AST scan for `customElements.define` with expected tag
- No framework detection heuristics; purely structural validation

**Props/Attributes:**
- Simple props: passed as attributes (strings, numbers, booleans)
- Complex props: JSON-serialized in `data-props` attribute, parsed by component
- Component reads `data-props` on connect, re-parses on attribute change

**Events:**
- `continuum:ready` — component mounted and ready (detail: `{ componentId }`)
- `continuum:error` — component error (detail: `{ componentId, error }`)
- Custom events: `continuum:{action}` pattern (e.g., `continuum:navigate`, `continuum:command`)

**Shadow DOM policy (V1):**
- Shadow DOM OFF for plugin components (easier token propagation, simpler styling)
- Plugins consume design tokens via CSS custom properties inherited from shell
- Svelte `customElement` config: `shadow: 'none'`
- Plugins MUST NOT depend on global selectors (e.g., `body`, `html`, `*`)

**M0 feasibility proof (Shadow DOM OFF):**
- Build one sample Svelte WC with `shadow: 'none'`
- Confirm: CSS tokens (`var(--continuum-*)`) propagate into component
- Confirm: Component styles don't leak and break shell layout

**Pivot clause (if shadow-off doesn't work cleanly):**
- Switch to shadow ON (`shadow: 'open'`)
- Tokens still work: CSS custom properties cross shadow boundaries
- Require plugins to NOT depend on global selectors (already a rule)
- Document the pivot decision; don't block V1 progress

**Fallback behavior:**
- If custom element not defined → shell renders placeholder with error message
- Acceptance tested: unknown tag does not white-screen the shell

### Plugin Package Layout (V1)

```
plugins/
  continuum.sample_signal/              # Directory uses plugin ID
    plugin.toml                         # Manifest (Python-side reads this)
    __init__.py                         # Python entrypoint (registers contributions)
    ui/
      src/
        SignalTimeline.svelte           # Svelte source
        SignalMetrics.svelte
      dist/
        continuum-sample-signal-timeline.js   # Compiled WC
        continuum-sample-signal-metrics.js
      package.json                      # UI build config
```

**Manifest references UI tags:**
```toml
[plugin]
id = "continuum.sample_signal"          # Dot-separated vendor.name
name = "Signal Dashboard"
version = "0.1.0"
required = false                        # Optional plugin

# Derived: ui_tag_prefix = "continuum-sample-signal" (dots → hyphens)

[ui]
components = [
  { tag = "continuum-sample-signal-timeline", file = "ui/dist/continuum-sample-signal-timeline.js" },
  { tag = "continuum-sample-signal-metrics", file = "ui/dist/continuum-sample-signal-metrics.js" }
]
```

**Dev workflow:**
- Plugin UI: `cd plugins/sample_signal/ui && npm run dev` (Vite hot-reload)
- Shell consumes compiled bundles via symlink or workspace reference
- V1: pnpm workspace linking between shell and plugin UI packages
- Build: `npm run build` compiles Svelte → Web Component bundles

### CSS Design Tokens

**Shell owns tokens:**
- `tokens.css` loaded by shell, defines all CSS custom properties
- Plugins MUST NOT include global resets or override token values
- Plugins consume tokens via `var(--continuum-*)` properties

**Token categories:**
- `--continuum-bg-*` — background colors
- `--continuum-text-*` — text colors
- `--continuum-accent-*` — accent/brand colors
- `--continuum-border-*` — borders
- `--continuum-radius-*` — border radii
- `--continuum-spacing-*` — spacing scale

### Capacitor iOS Constraints (V1)

**Auth/session:**
- Token-based auth (not cookies) for WebView compatibility
- Tokens stored via Capacitor Preferences API (not localStorage for security)
- Shell handles token refresh; plugins receive context via props

**CORS/CSP:**
- API must allow requests from `capacitor://localhost` origin
- CSP configured to allow Capacitor bridge scripts

**Deep linking:**
- `/{perspective}/...` routes work in WebView
- Capacitor App plugin handles universal links → internal navigation
- Shell exposes `navigate(path)` method for plugins

**Constraints documented, not fully implemented in V1** — but API/shell must not make choices that break Capacitor later.

### OpenAPI Contract Governance

- OpenAPI spec generated from FastAPI, versioned in repo
- `host_api_version` in plugin manifest specifies compatible API version range
- **Breaking change rules:**
  - Removing/renaming endpoints = major version bump
  - Removing/renaming response fields = major version bump
  - Adding optional fields = minor version bump
- Shell validates `host_api_version` compatibility on boot; incompatible plugins marked FAILED

### Drift Prevention

1. **OpenAPI spec** — Backend generates spec; shells are consumers; versioned
2. **Web Component contract** — Tag naming, props, events frozen in M0
3. **Design tokens** — Single `tokens.css` as source of truth
4. **Visual regression** — Playwright screenshots against `tests/visual/sample_dashboard.html`
5. **Contract tests** — Validate plugin manifests, WC compliance, and contribution schemas in CI

---

## Pre-Milestone: Decisions to Lock

Before starting M0, resolve these:

1. **Canonical ID namespace:** Use `ui.slot.*` for Switchboard Slot IDs. "Region" is the UX term in docs/UI only; APIs and registries use Slot IDs exclusively.

2. **UI packaging (V1):** Compile-time bundling. Host imports plugin UI components at build time. Design a clean seam so runtime loading can be added later, but do not implement runtime loading in V1.

3. **Conflict policy for ONE slots:** Winner by priority (highest wins); ties broken by plugin load order (deterministic). Emit conflict warnings in registry build report.

4. **Web Component compilation:** All plugin UI components MUST export as Web Components. Svelte components use `<svelte:options customElement="continuum-*"/>` pattern.

---

## M0: Shell Boot

**Goal:** Establish the core runtime skeleton with lifecycle management, base contracts, and diagnostics.

### Tasks

#### Project Setup
- Initialize `pyproject.toml` with project metadata and dependencies
- Configure Switchboard dependency (git reference + local editable for dev)
- Set up dev tooling (pytest, ruff/black, mypy)

#### Host Contracts (Freeze Early)
- **PluginManifest schema:**
  - Required fields: id, name, version, description, entrypoint
  - Version fields: `host_api_version` (semver range this plugin requires), `plugin_api_version` (this plugin's version)
  - Lifecycle fields: `required` (bool, default false) — if true, plugin failure triggers DEGRADED
  - UI fields: `components` (list of tag + file mappings)
  - Validation: unique plugin IDs, semver parsing, referenced UI files exist
- **Contribution schemas** (stable shapes, even if not fully used until M1):
  - `PanelContribution`: id, slot_id, component, props, priority, perspective_scope (optional), required (bool, default false)
  - `NavContribution`: id, group, label, icon, target, required (bool, default false) — where target is one of:
    - `{ type: "perspective", perspective_id }` — switch to perspective (swaps main panel assembly)
    - `{ type: "route", path }` — navigate to route
    - `{ type: "action", action_id }` — trigger action (open modal, drawer, etc.)
    - Note: NavContribution does NOT have perspective_scope in V1 (all nav items visible in all perspectives; scoping deferred to V2)
  - `DrawerContribution`: id, slot_id (`ui.slot.drawer`), component, props, trigger_action_id, required (bool, default false)
  - `CommandContribution`: id, label, input_schema, required_capabilities, handler, danger_level (safe|confirm|danger), audit_redaction (list of arg keys), idempotency_hint (optional), dry_run_supported (bool, default false)
  - `DiagnosticContribution`: id, health_check, version_info
- **ID conventions:**
  - Plugin IDs: `vendor.plugin_name` (dot-separated, e.g., `acme.signal_dashboard`)
  - **UI tag prefix:** Derived from plugin_id by replacing dots with hyphens: `acme.signal_dashboard` → `acme-signal-dashboard`
  - Web Component tags: `continuum-{ui_tag_prefix}-{component_name}` (e.g., `continuum-acme-signal-dashboard-timeline`)
  - Contribution IDs: `plugin_id.contribution_type.name` (e.g., `acme.signal_dashboard.panel.overview`)
  - Capability namespaces: `domain.action` (e.g., `squadops.deploy`, `nebulus.restart`)
  - **Validation:** Manifest validation rejects plugin IDs that produce invalid tag prefixes (must result in valid custom element name)
- **Registry payload contract** (stable shape for UI):
  ```json
  {
    "lifecycle_state": "READY",
    "registry_fingerprint": "<hash>",
    "perspectives": [...],
    "regions": {
      "ui.slot.left_nav": [...],
      "ui.slot.main": [...]
    },
    "commands": [...],
    "plugins": [...],
    "diagnostics": {
      "conflicts": [...],
      "missing_required": [...],
      "warnings": [...]
    }
  }
  ```
- **Contract test suite:** JSON schema validation for manifests, contributions, and registry payload. Run in CI.

#### Lifecycle State Machine
- States: `BOOTING`, `DISCOVERING_PLUGINS`, `LOADING_PLUGINS`, `RESOLVING_REGISTRY`, `READY`, `DEGRADED`, `STOPPING`, `STOPPED`
- `LifecycleManager` class with explicit state transitions
- Structured events on each transition (stable event names for telemetry):
  - `continuum.lifecycle.transition` (from_state, to_state, timestamp)
  - `continuum.lifecycle.error` (state, error, context)

#### DEGRADED Mode Semantics
- **Triggers for DEGRADED:**
  - Plugin with `required: true` fails to load
  - Contribution with `required: true` fails to register (regardless of slot optionality)
  - REQUIRED slot has no contributions
  - Registry resolution hard failure (e.g., cycle detection, schema violation)
- **Precedence rule:** `contribution.required` takes precedence over slot optionality
  - A required contribution in an OPTIONAL slot still triggers DEGRADED if it fails
  - Rationale: Plugin authors can mark critical contributions even in optional regions
- **Warnings only (not DEGRADED):**
  - Optional plugin load failure → READY with warning
  - Optional contribution in optional slot fails → READY with warning
  - ONE-slot conflict on OPTIONAL slot → winner selected, warning logged
- **Slot definitions:**
  - REQUIRED slots: missing contributions → DEGRADED
  - OPTIONAL slots: missing contributions → READY with warnings (unless a required contribution failed)
- **Failure list in diagnostics:** plugin failures (with required flag), missing required slots, failed required contributions, conflicts (with winner/loser), warnings

#### Base Domain Models
- `PerspectiveSpec` dataclass (id, label, route_prefix, regions)
- Define five core perspectives: Signal, Research, Time, Discovery, Systems
- `RegionSpec` dataclass with slot_id, cardinality (ONE|MANY), required (bool)

#### Region Slot Definitions (V1)
Define the complete slot inventory for the shell layout (single source of truth):
- `ui.slot.left_nav` (MANY) — Perspective switcher + action triggers
- `ui.slot.header` (ONE) — Title, search, user profile
- `ui.slot.main` (MANY) — Primary content area, perspective-scoped panel assembly
- `ui.slot.right_rail` (MANY) — Secondary panels (activity feeds, lists)
- `ui.slot.footer` (ONE) — Status bar, system info
- `ui.slot.modal` (MANY) — Overlay dialogs (command palette, confirmations)
- `ui.slot.drawer` (MANY) — Slide-in panels (agent chat, detail views)
- `ui.slot.toast_stack` (MANY) — Transient notifications, stacked bottom-right

**Visual reference:** See `tests/visual/sample_dashboard.html` for target aesthetic and layout.

#### Diagnostics Endpoints
- `GET /health` — lifecycle state, basic health indicator
- `GET /diagnostics` — runtime info, failure list, missing slots, conflicts
- `GET /api/registry` — stable registry payload (returns empty/placeholder initially)

#### Security Baseline (API)
Token-based auth model (not cookie-based sessions):
- **CORS:** Strict origin allowlist — shell origin + `capacitor://localhost`; reject others
- **Authorization:** Bearer token in `Authorization` header; validated on every request
- **Content-Type enforcement:** Reject requests without proper `Content-Type: application/json`
- **Request validation:** Validate all input against schemas; reject malformed payloads
- **Auth (V1):** Mock auth adapter returns static user context; real auth is adapter-swappable
- **No CSRF tokens needed:** Token auth via header (not cookies) is not vulnerable to CSRF
- **Documented posture:** Security seams exist so real auth drops in later

#### Runtime & Dev Workflow

**Production mode: `continuum run`**
```bash
# Build shell first (if not already built)
cd web && npm run build && cd ..

# Start server (default port: 4040)
continuum run
# → FastAPI serves API on /api/* and static shell on /*
# → Open http://localhost:4040

# Custom port
continuum run --port 9000
# Or: CONTINUUM_PORT=9000 continuum run
```
- Single process, single port (default :4040)
- FastAPI serves pre-built SvelteKit assets from `web/build/`
- Plugin UIs bundled at build time

**Development mode: `continuum dev`**
```bash
# Terminal 1: API server with auto-reload (default: 4040)
continuum dev --api-only
# Or: cd src/continuum && uvicorn main:app --reload --port 4040

# Terminal 2: SvelteKit dev server with hot reload
cd web && npm run dev
# → Shell on http://localhost:5173
# → Vite proxies /api/* to http://localhost:4040
```
- Two processes for fast iteration
- SvelteKit hot reload for UI changes
- Uvicorn reload for Python changes

**Port configuration:**
- Default: `4040` (less commonly used)
- CLI flag: `--port`
- Environment variable: `CONTINUUM_PORT`

**Vite proxy config (web/vite.config.ts):**
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:4040',
      '/health': 'http://localhost:4040',
      '/diagnostics': 'http://localhost:4040'
    }
  }
});
```

**Build commands:**
- `npm run build` — Build SvelteKit shell to `web/build/`
- `npm run build:plugins` — Build all plugin UIs to their `dist/` folders
- `continuum build` — Orchestrates full build (plugins + shell + verification)

#### Smoke Test
- Lifecycle transitions BOOTING → READY with expected events emitted
- Health endpoint returns expected state
- Registry endpoint returns valid schema (even if empty)

### Deliverables
- Runnable server process that boots and reports READY
- Frozen host contracts (manifest, contributions, registry payload)
- Contract test suite passing
- Health, diagnostics, and registry endpoints functional
- Core perspectives defined (no UI yet)

---

## M1: Plugin Runtime

**Goal:** Load plugins, register contributions into Switchboard PatchPanel, build the contribution registry with deterministic resolution, and provide early introspection.

### Tasks

#### Plugin Manifest Validation
- Semver parsing for host_api_version compatibility checks
- Unique plugin ID enforcement (fail on collision)
- Unique contribution ID enforcement within plugin
- Capability namespace validation (warn on likely collisions)

#### Plugin Discovery
- Scan configured plugin directories
- **Deterministic discovery order:** alphabetical by plugin directory name, then by manifest ID
- Validate manifests, collect discovered plugins
- Handle discovery failures gracefully (log, mark as FAILED, continue)

#### Plugin Loader
- Import plugin entrypoint modules
- Execute registration functions with PatchPanel reference
- Track load success/failure per plugin with timing info
- **Deterministic load order:** matches discovery order

#### Contribution Registration
- Register contributions to PatchPanel slots
- **Deterministic ordering rules:**
  - Primary: priority (highest first)
  - Secondary: `discovery_index` (stable tiebreaker)
- **discovery_index:**
  - Assigned during plugin discovery (alphabetical by dir, then manifest ID)
  - Persisted in diagnostics and registry payload
  - Makes conflicts reproducible: "Plugin A (index 3) beat Plugin B (index 7) for slot X"
- **Cardinality enforcement:**
  - ONE: first contributor wins by priority, then discovery_index; log conflict with indices
  - MANY: ordered list by priority, then discovery_index

#### Registry Builder
- Resolve all contributions from PatchPanel
- Apply ordering rules
- **Registry build report:**
  - Counts per slot
  - Conflicts: slot_id, winners, losers (with plugin IDs)
  - Missing required slots
  - Warnings
- **Registry fingerprint:** hash of (sorted manifest hashes + resolved registry state) for reproducibility

#### Plugin Status Tracking
- Per-plugin status: DISCOVERED, LOADING, LOADED, FAILED, DISABLED
- Failure reason stored for FAILED plugins
- **DISABLED mechanism:**
  - Plugins can be disabled via config (not just failure)
  - DISABLED is deterministic — same config = same disabled set
  - DISABLED plugins do not contribute to registry, do not trigger DEGRADED
  - Use case: temporarily disable a plugin without removing it
- Surface in `/diagnostics` endpoint

#### Build-Time Verification (V1)
Registry validity is guaranteed at build time, not runtime.

**Bundling mechanism (Vite glob import):**
```typescript
// web/src/lib/plugin_bundles.ts (generated by continuum build)
// Imports all plugin UI bundles so they're included in the shell build

import 'plugins/continuum.sample_signal/ui/dist/continuum-sample-signal-timeline.js';
import 'plugins/continuum.sample_signal/ui/dist/continuum-sample-signal-metrics.js';
// ... all plugin bundles
```
- `continuum build` generates this file by scanning plugin manifests
- Vite includes these in the shell bundle
- Alternative: Vite glob import `import.meta.glob('../../plugins/**/ui/dist/*.js', { eager: true })`

**Verification steps:**
1. **Directory = ID:** Plugin directory name must equal `plugin.id` in manifest (fail fast on mismatch)
2. **File existence:** Every manifest `ui.components[].file` path exists
3. **Bundle inclusion:** Generated `plugin_bundles.ts` includes all declared files
4. **Tag declaration:** Each bundle defines its tag via `customElements.define('{tag}', ...)`
   - Grep/AST scan for the define call with expected tag string

**Build fails if:**
- Plugin directory name ≠ plugin.id
- Manifest references non-existent UI file
- UI file doesn't declare the expected tag
- Tag name is invalid custom element name

**Runtime implication:** If build succeeds, registry is valid by construction. No runtime tag existence checks needed.

**`continuum build` is canonical:**
- Produces the distributable artifacts (shell + bundled plugins)
- `continuum run` consumes the same resolved inputs
- Registry fingerprint matches between build and run

#### Early Introspection (Minimal Systems Surface)
- `GET /api/registry` now returns real resolved data
- **CLI command:** `continuum inspect`
  - List plugins with status
  - List resolved slots with contributors
  - Show conflicts and warnings
- Simple HTML viewer at `/debug/registry` (dev mode only) — optional but helpful

#### Sample Plugins
Sample plugins use the `continuum` vendor prefix to follow ID conventions:

- `continuum.sample_signal` — PanelContributions to `ui.slot.main` with `perspective_scope: "signal"`
  - Tag prefix: `continuum-sample-signal`
  - Tags: `<continuum-sample-signal-metrics>`, `<continuum-sample-signal-timeline>`
  - Exercises ordering (multiple panels with different priorities)
- `continuum.sample_systems` — PanelContributions to `ui.slot.main` with `perspective_scope: "systems"`
  - Plugin status, registry inspector panels
- `continuum.sample_nav` — NavContributions to `ui.slot.left_nav`:
  - Perspective switchers (Signal, Research, Time, Discovery, Systems)
  - Action triggers (command palette, agent chat)
- `continuum.sample_command` — CommandContribution with stub handler (end-to-end execution test)
- `continuum.sample_chat` — DrawerContribution to `ui.slot.drawer` (agent chat panel, triggered by nav action)
- `continuum.sample_diagnostics` — DiagnosticContribution with health check

### Deliverables
- Plugins discovered and loaded with deterministic order
- Contributions registered in PatchPanel with deterministic resolution
- Registry fingerprint available for reproducibility checks
- `continuum inspect` CLI functional
- Registry build report includes conflicts (winners/losers)
- Sample plugins covering all contribution types
- Contract tests for ordering determinism

---

## M2: UI Rendering

**Goal:** Build the web UI that consumes the registry and renders contributions into regions.

### Prerequisites
- Stable registry payload contract (from M0)
- At least 2 sample plugins loaded and resolved (from M1)
- UI packaging decision locked: compile-time bundling

### Tasks

#### UI Framework Setup
- Initialize SvelteKit project with TypeScript
- Configure Vite build pipeline (SvelteKit default)
- Set up component library foundation
- Configure Web Component compilation (`svelte.config.js` customElement settings)

#### Component Registry Contract
- **Tag naming:** Per M0 contract — `{ui_tag_prefix}-{component-name}` (e.g., `<continuum-sample-signal-timeline>`)
- **Registry provides full tag:** UI reads `component` field from registry and renders directly
- **No runtime transformation:** `<svelte:element this={contribution.component}>` uses the exact tag string
- **Fallback rendering:** Unknown tags render a placeholder with error message (not white screen)
- **Component interface:** Standard props via attributes + custom events for callbacks
- **Svelte compilation:** Each plugin component uses `<svelte:options customElement="{tag}" />`

#### Shell Layout
- Base shell with region containers
- Regions: header, left_nav, main, right_rail, footer, modal, toast_stack
- Responsive layout adapting to viewport
- Region containers handle cardinality (ONE renders single, MANY renders list)

#### Perspective Routing and Panel Assembly
- Route structure: `/{perspective}/...`
- **Perspective switcher in left nav** — NavContributions with `target.type: "perspective"`
- Deep-linking support
- **Perspective-scoped panel assembly:**
  - When perspective changes, `ui.slot.main` renders only panels with matching `perspective_scope`
  - Panels without `perspective_scope` render in all perspectives (global panels)
  - This enables each perspective to have its own curated panel assembly
- Nav contributions can target:
  - Perspective switch (swaps main panel assembly)
  - Route (navigate to URL)
  - Action (open drawer, modal, trigger command)

#### Region Rendering Engine
- Fetch registry on boot via `/api/registry`
- Render Web Components dynamically using `<svelte:element this="continuum-...">` or direct DOM insertion
- Apply cardinality rules per slot (ONE vs MANY)
- Apply priority ordering from resolved registry
- Handle missing/failed components gracefully (custom element not defined → placeholder)

#### Runtime Loading Seam (documented, not implemented)
V1 uses compile-time bundling. Document where runtime loading would attach for future:
- **ComponentLoader interface:** `loadComponent(tag: string, bundleUrl: string): Promise<void>`
- **Registry extension:** `component` field could include `bundleUrl` for remote loading
- **V1 behavior:** ComponentLoader is a no-op; all components pre-registered at build time
- **Future behavior:** ComponentLoader fetches and registers Web Components on demand
- This seam exists in code as an interface; implementation is stubbed for V1

#### Navigation Contributions
- Render nav items from NavContribution data
- Group by perspective
- Active state based on current route/panel

#### Drawer (Slide-in Panel) Rendering
- `ui.slot.drawer` renders slide-in panels from right edge
- DrawerContributions specify a `trigger_action_id`
- When NavContribution targets `{ type: "action", action_id }`, matching drawer slides in
- Drawer state: open/closed, managed by shell
- Escape key closes active drawer
- Example: Agent Chat panel slides in when chat action triggered

#### UI Component Library (Svelte)
- Base panel container component (`Panel.svelte`)
- Nav item component with icon + tooltip (`NavItem.svelte`)
- Drawer container with slide-in animation (`Drawer.svelte`)
- Modal/overlay container (`Modal.svelte`)
- Placeholder/loading states (`Placeholder.svelte`)
- Error boundary wrapper for Web Component failures
- All shell components are internal Svelte (not Web Components) for performance

### Deliverables
- Web UI renders shell with all regions
- Perspectives navigable via left nav (panel assembly swaps)
- Sample plugin panels render in correct regions with perspective scoping
- Nav contributions appear in left nav (perspectives + actions)
- Drawer panels slide in when triggered
- Modal overlays render above content
- Fallback rendering for unknown/broken components
- Deep-linking functional
- **Matches target aesthetic:** `tests/visual/sample_dashboard.html`

---

## M3: Command Surface

**Goal:** Implement the unified command execution pipeline with authorization, guardrails, and audit logging.

### Tasks

#### Command Registry
- Collect CommandContributions from plugins
- Index by command ID
- Expose via `/api/registry` (commands array)
- Include metadata: danger_level, required_capabilities, input_schema

#### Command Palette UI
- Global command palette (keyboard shortcut: Cmd/Ctrl+K)
- Search/filter commands by label, ID
- Display: label, danger level indicator, required capabilities
- Confirmation step for `confirm` and `danger` level commands

#### Execution Endpoint
- `POST /api/commands/execute`
- Request: `{ command_id, args, context }`
- Validate input against command's input_schema
- **Structured response:**
  ```json
  {
    "audit_id": "<uuid>",
    "status": "success|failure|denied",
    "started_at": "<iso8601>",
    "duration_ms": 123,
    "result_summary": "...",
    "error_summary": "..."
  }
  ```

#### Authorization
- `UserContext` model: id, roles, claims
- `PolicyDecision` model: allow/deny, rationale
- Policy check before execution
- **Deny-by-default:** Unknown capabilities → deny with logged rationale
- Auth adapter interface (pluggable); mock implementation for V1

#### Command Bus
- Route command to handler (local or proxy-to-target)
- Handle timeouts gracefully
- Structured result/error reporting

#### Target Adapters
- HTTP adapter for REST API targets
- CLI adapter for command-line targets
- Adapter interface for future expansion (message bus, etc.)

#### Audit Logging
- Log all executions: audit_id, user_context, command_id, args (with redaction), start, duration, outcome
- **Redaction:** Honor `audit_redaction` field from CommandContribution
- Store recent executions for diagnostics viewer
- Emit structured audit events: `continuum.command.executed`

#### Guardrails
- Danger level metadata enforced in UI (confirmation dialogs)
- **Dry run support:** `dry_run_supported` field on CommandContribution
  - If true, UI shows "Dry Run" option alongside "Execute"
  - Dry run passes `{ dry_run: true }` in command context
  - Handler returns preview of what would happen without side effects
  - V1: UI messaging only; handlers may ignore dry_run flag initially
- **Rate limiting:** Design fields in command contribution (`rate_limit_key`, `rate_limit_window`) but do not implement enforcement in V1. Leave extension seam.

### Deliverables
- Command palette functional in UI
- Commands execute through authorization pipeline
- Audit log captures all executions with redaction
- Deny-by-default works with logged rationale
- sample_command executes end-to-end (authorized + denied cases)
- Structured execution reports returned

---

## M4: Systems Perspective

**Goal:** Build the introspection and diagnostics UI for operators to understand system state.

### Prerequisites
- Plugin status data from M1
- Registry build report from M1
- Audit log from M3

### Tasks

#### Plugin Status Panel
- Table view of all plugins
- Columns: name, version, status, load time, contribution count
- Filter by status (loaded/failed/disabled)
- Expandable row with failure details

#### Registry Inspector
- Tree view: perspectives → regions → contributions
- Contribution details: source plugin, priority, component key
- Highlight conflicts (show winner and losers)
- Show missing required slots
- Registry fingerprint display

#### Health Dashboard
- Overall system health indicator (READY/DEGRADED with reason)
- Lifecycle state display
- Uptime and basic metrics

#### Diagnostics Viewer
- Last registry build report (conflicts, warnings, counts)
- Recent lifecycle transitions
- Error/warning log viewer

#### Command Audit Viewer
- Recent command executions table
- Columns: timestamp, command, user, status, duration
- Filter by command, user, outcome
- Expandable row with execution details (redacted args, result/error summary)

#### Systems Perspective Layout
- Wire panels into Systems perspective regions
- Nav items for each panel
- Default landing: Health Dashboard

### Deliverables
- Systems perspective fully functional
- Operators can inspect plugin status and registry
- Conflicts and missing slots visible
- Health and diagnostics accessible
- Command audit trail browsable

---

## Testing Strategy

### Golden E2E Smoke Test (CI + Local)

Run on every commit:

1. Boot → READY (or DEGRADED with expected failures)
2. Verify deterministic registry fingerprint (same inputs → same hash)
3. Discover + load ≥2 plugins
4. Resolve registry: expected slots populated and ordered correctly
5. `GET /api/registry` returns valid schema
6. Execute sample command (authorized case) → success + audit entry
7. Execute sample command (denied case) → denied + audit entry with rationale

### Contract Tests (Fast Unit Tests)

- Plugin manifest schema validation (valid + invalid cases)
- Plugin ID → tag prefix transform validation (dots to hyphens, valid custom element names)
- Contribution schema validation
- Slot cardinality enforcement (ONE vs MANY behavior)
- Deterministic ordering (same inputs → same outputs, run 10x)
- Conflict policy behavior for ONE slots (winner/loser assignment with discovery_index)
- Registry payload schema compatibility
- Semver range matching for host compatibility
- DISABLED plugin exclusion (disabled plugins don't contribute)

### Required/Optional Acceptance Tests (Named)

```
test_required_plugin_failure_triggers_degraded
  - Given: plugin with required=true
  - When: plugin fails to load
  - Then: lifecycle state = DEGRADED

test_optional_plugin_failure_stays_ready
  - Given: plugin with required=false
  - When: plugin fails to load
  - Then: lifecycle state = READY, warning logged

test_required_slot_empty_triggers_degraded
  - Given: slot with required=true, no contributions
  - When: registry resolves
  - Then: lifecycle state = DEGRADED

test_optional_slot_empty_stays_ready
  - Given: slot with required=false, no contributions
  - When: registry resolves
  - Then: lifecycle state = READY, warning logged

test_required_contribution_in_optional_slot_triggers_degraded
  - Given: contribution with required=true in optional slot
  - When: contribution fails to register
  - Then: lifecycle state = DEGRADED (contribution.required takes precedence)

test_optional_contribution_in_optional_slot_stays_ready
  - Given: contribution with required=false in optional slot
  - When: contribution fails to register
  - Then: lifecycle state = READY, warning logged

test_one_slot_conflict_required_slot
  - Given: ONE slot with required=true, two contributors
  - When: registry resolves
  - Then: winner by priority+discovery_index, loser logged, state = READY (conflict is warning, not DEGRADED)

test_one_slot_conflict_optional_slot
  - Given: ONE slot with required=false, two contributors
  - When: registry resolves
  - Then: winner by priority+discovery_index, loser logged, state = READY
```

### Web Component Contract Tests

- Component tag exists after build (build-time verification)
- Required events emitted: `continuum:ready` on mount
- Error event emitted: `continuum:error` on failure
- Props decode successfully (simple attrs + JSON `data-props`)
- Unknown tag renders placeholder (no white-screen)
- CSS tokens inherited (custom properties accessible in component)

### Build Determinism Tests

- Registry fingerprint stable across 10 consecutive boots (same config)
- Plugin discovery order deterministic (alphabetical)
- Contribution ordering deterministic (priority + load order tiebreaker)
- DISABLED state deterministic (same config = same disabled set)

### Per-Milestone Tests

- **M0:** Lifecycle transitions emit correct events; contract schemas validate
- **M1:** Plugin discovery order deterministic; registry fingerprint stable
- **M2:** Component fallback renders for unknown keys; deep-links resolve
- **M3:** Redaction applied correctly; deny-by-default triggers
- **M4:** UI renders data from M1/M3 correctly

---

## Documentation Deliverables

### After M1: "Write a Plugin" Quickstart
- Manifest structure with examples
- Entrypoint registration pattern
- Contribution examples (one per type)
- Local development workflow

### After M3: "Command Contribution Guide"
- Capabilities and permission model
- Danger levels and when to use each
- Audit and redaction expectations
- Handler implementation patterns

---

## Suggested Sequence

```
Week 1-2:  M0 (Shell Boot + Contracts)
Week 3-5:  M1 (Plugin Runtime + Early Introspection)
Week 6-8:  M2 (UI Rendering)
Week 9-11: M3 (Command Surface)
Week 12:   M4 (Systems Perspective)
Week 13+:  Polish, testing, documentation
```

---

## Success Criteria (V1 Complete)

- [ ] New surface can be added as a plugin without changing Continuum core
- [ ] Operator can navigate to tools by perspective and region
- [ ] Shell can explain its wiring (installed plugins, active contributions, commands)
- [ ] Navigation and layout feel stable
- [ ] Control plane is safer than ad-hoc scripts and one-off admin panels
- [ ] Golden smoke test passes end-to-end
- [ ] Contract tests prevent schema drift
- [ ] Registry fingerprint is reproducible across restarts
- [ ] "Write a Plugin" quickstart enables external contributors
