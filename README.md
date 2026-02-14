# Continuum

A plugin-driven control-plane UI shell that hosts multiple operational surfaces behind consistent navigation, auth, and extensibility.

## Overview

Continuum provides a unified operator experience for managing multiple systems. Instead of scattered dashboards and inconsistent navigation, Continuum offers:

- **Perspectives** — Curated work modes (Signal, Research, Time, Discovery, Systems)
- **Plugin architecture** — Add surfaces without modifying core
- **Command system** — Safe operator actions with audit logging, permissions, and danger levels
- **Strong introspection** — Always know what's installed, active, and wired

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### Installation

```bash
# Install Python dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd web && npm install && cd ..

# Build plugin UIs
./scripts/build-plugins.sh
```

### Running

```bash
# Start the server (API + static frontend)
continuum run --reload

# Or run API and frontend separately for development:
continuum dev          # Terminal 1: API on :4040
cd web && npm run dev  # Terminal 2: Vite on :5173
```

Open http://localhost:4040 (or :5173 in dev mode).

## Project Structure

```
continuum/
├── src/continuum/          # Python backend (FastAPI)
│   ├── domain/             # Core models (perspectives, regions, commands)
│   ├── app/                # Runtime, discovery, loader, registry
│   └── adapters/           # Web API, auth, telemetry
├── web/                    # SvelteKit frontend
│   └── src/lib/            # Components, stores, services
├── plugins/                # Sample plugins
├── tests/                  # Test suite
└── docs/                   # Documentation
```

## Writing Plugins

Plugins live in `plugins/` with a `plugin.toml` manifest and `__init__.py` entry point.

```toml
# plugins/my.plugin/plugin.toml
[plugin]
id = "my.plugin"
name = "My Plugin"
version = "1.0.0"

[[contributions.nav]]
slot = "ui.slot.left_nav"
label = "My Feature"
icon = "activity"

[contributions.nav.target]
type = "panel"
panel_id = "signal"
```

```python
# plugins/my.plugin/__init__.py
def register(ctx):
    ctx.register_contribution("command", {
        "id": "my_action",
        "label": "My Action",
        "action": "my_handler",
        "danger_level": "safe",
    })
```

See [docs/plugin-quickstart.md](docs/plugin-quickstart.md) for the full guide.

## Commands

The command system provides safe operator actions:

- **Danger levels**: `safe` (immediate), `confirm` (requires confirmation), `danger` (prominent warning)
- **Capabilities**: Role-based authorization
- **Audit logging**: All executions logged with redaction support
- **Dry-run**: Preview mode for destructive operations

See [docs/command-guide.md](docs/command-guide.md) for details.

## CLI

```bash
continuum run [--port 4040] [--reload]  # Start server
continuum dev                            # Dev mode (API only)
continuum inspect [--json]               # Inspect plugins and registry
```

## Testing

```bash
pytest tests/ -v
```

## Documentation

- [Architecture Specification](docs/CONTINUUM_V1_ARCH_SPEC.md)
- [Plugin Quickstart](docs/plugin-quickstart.md)
- [Command Guide](docs/command-guide.md)
- [Design Intent](docs/CONTINUUM_INTENT_DOC.md)

## License

Private
