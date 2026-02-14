# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Continuum?

Continuum is a **plugin-driven control-plane UI shell** (Python FastAPI backend + SvelteKit frontend) that hosts multiple operational "surfaces" (dashboards, consoles, workflows) behind consistent navigation, auth, and extensibility. It's the "desktop" for operators—not another standalone app.

## Commands

### Backend (Python)

```bash
# Install dependencies (editable mode with dev extras)
pip install -e ".[dev]"

# Start server with auto-reload
continuum run --reload

# Dev mode (API only, use with Vite dev server)
continuum dev

# Inspect plugins/registry without starting server
continuum inspect [--json]
```

### Frontend (SvelteKit)

```bash
cd web
npm install
npm run dev       # Vite dev server with HMR
npm run check     # Type checking (svelte-check)
npm run build     # Production build
```

### Testing

```bash
pytest tests/ -v                    # All tests
pytest tests/test_smoke.py -v       # Smoke tests only
pytest tests/test_commands.py -v    # Command system tests
```

### Plugin UI Builds

```bash
./scripts/build-plugins.sh          # Build all plugin UI bundles
# Or per-plugin:
cd plugins/{plugin_id}/ui && npm run build
```

## Architecture

### Runtime Lifecycle

The runtime progresses through states: `BOOTING` → `DISCOVERING_PLUGINS` → `LOADING_PLUGINS` → `RESOLVING_REGISTRY` → `READY` (or `DEGRADED` on errors) → `STOPPING` → `STOPPED`.

### Plugin System

1. **Discovery**: Scans `./plugins/` alphabetically for `plugin.toml` manifests
2. **Loading**: Imports each plugin's `__init__.py` and calls `register(ctx)`
3. **Registry**: Contributions are collected and resolved by slot cardinality (ONE vs MANY) and priority

Plugins contribute: **Nav** (navigation items), **Panel** (main/rail content), **Drawer** (slide-in panels), **Command** (executable actions), **Diagnostic** (health checks).

### Key Files

- `src/continuum/app/runtime.py` — Main orchestrator (lifecycle, boot sequence)
- `src/continuum/app/registry.py` — Contribution resolution and conflict handling
- `src/continuum/app/command_bus.py` — Command execution pipeline
- `src/continuum/domain/` — Read-only domain models (perspectives, regions, contributions, commands)
- `web/src/lib/components/Shell.svelte` — Main UI shell layout
- `web/src/lib/stores/registry.ts` — Svelte store for registry state

### Perspectives and Regions

Perspectives are curated work modes: `signal`, `research`, `time`, `discovery`, `systems`.

Regions are fixed UI anchors (slots): `ui.slot.left_nav`, `ui.slot.header`, `ui.slot.main`, `ui.slot.right_rail`, `ui.slot.footer`, `ui.slot.modal`, `ui.slot.drawer`, `ui.slot.toast_stack`.

### Plugin UI Architecture

Plugin UIs compile Svelte to Web Components (custom elements). Bundles are served from `/plugins/{plugin_id}/assets/plugin.js` and loaded dynamically. The `tag_prefix` in `plugin.toml` determines custom element names.

### Command Execution Flow

Request → Lookup → Authorization (capabilities) → Input validation (JSON Schema) → Confirmation check (danger levels: safe/confirm/danger) → Dry-run preview → Handler dispatch (timeout-protected) → Audit logging → Response.

## Architectural Principles

- **Host-owned seams**: Continuum defines perspectives/regions; plugins contribute to them (never invent new core navigation)
- **Boundary discipline**: Continuum is a UI shell, not a domain layer—business logic stays in underlying systems
- **Deterministic extensibility**: Plugins register via context object, no global state mutations
- **Strong introspection**: Always answer "what's installed, active, and wired where?" via `/diagnostics`, `/api/registry`, or `continuum inspect`
- **Fail-safe degradation**: Plugin failures don't crash host; runtime enters DEGRADED state with diagnostics

## Useful Endpoints

- `/health` — Lifecycle state
- `/diagnostics` — Plugin status, warnings, errors
- `/api/registry` — Full resolved registry (perspectives, regions, commands)
- `/api/commands/execute` — Command execution

## Documentation

- `docs/CONTINUUM_V1_ARCH_SPEC.md` — Detailed architecture specification
- `docs/plugin-quickstart.md` — Plugin development guide
- `docs/command-guide.md` — Command system (permissions, danger levels, audit)
