# Write a Plugin: Quickstart Guide

This guide covers everything you need to create a Continuum plugin.

## Directory Structure

Plugins live in the `plugins/` directory. Each plugin has its own directory with a required `plugin.toml` manifest:

```
plugins/
  your.plugin_name/
    plugin.toml        # Required: plugin manifest
    __init__.py        # Required: Python entrypoint
    ui/                # Optional: UI components
      src/
        MyPanel.svelte
      vite.config.js
    dist/              # Built UI bundle output
      plugin.js
```

**Important:** The directory name MUST match the plugin ID in `plugin.toml`.

## Manifest Structure

The `plugin.toml` file defines your plugin and its contributions:

```toml
[plugin]
id = "your.plugin_name"              # Required: unique identifier
name = "My Plugin"                   # Required: display name
version = "1.0.0"                    # Required: semver version
description = "What this plugin does"
required = false                     # Optional: if true, failure triggers DEGRADED state

[plugin.ui]
tag_prefix = "your-plugin-name"      # Required: prefix for custom elements
bundle = "plugin.js"                 # Optional: path to built UI bundle
```

## Contribution Types

### Navigation Items

Add items to the left navigation bar:

```toml
[[contributions.nav]]
slot = "ui.slot.left_nav"
label = "My Feature"
icon = "activity"                    # Lucide icon name
priority = 100                       # Higher = appears first

[contributions.nav.target]
type = "panel"                       # Can be: panel, command, drawer
panel_id = "my_perspective"
```

Target types:
- `panel` - Switch to a perspective (panel_id matches perspective ID)
- `command` - Execute a command (command_id)
- `drawer` - Open a drawer (drawer_id)
- `route` - Navigate to a route (route path)

### Panels

Add panels to the main content area or right rail:

```toml
[[contributions.panel]]
slot = "ui.slot.main"                # or "ui.slot.right_rail"
perspective = "signal"               # Only show in this perspective
component = "your-plugin-name-panel" # Web component tag name
priority = 100
```

### Commands

Add executable commands:

```toml
[[contributions.command]]
id = "my_command"
label = "Do Something"
shortcut = "Ctrl+Shift+M"
action = "my_handler"
danger_level = "safe"                # safe, confirm, or danger
```

See the [Command Contribution Guide](command-guide.md) for full command documentation.

### Drawers

Add slide-in drawer panels:

```toml
[[contributions.drawer]]
id = "my_drawer"
component = "your-plugin-name-drawer"
title = "My Drawer Title"            # Optional: display title
width = "400px"                      # Optional: width (default: "400px")
```

### Themes

Add custom themes that appear in the shell's footer theme selector:

```toml
[[contributions.theme]]
id = "myapp-dark"
name = "My App Dark"
description = "Branded dark theme"
category = "dark"                    # "dark" or "light"
preview_colors = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#533483"]

[[contributions.theme]]
id = "myapp-light"
name = "My App Light"
description = "Branded light theme"
category = "light"
preview_colors = ["#fafafa", "#f0f0f5", "#0f3460", "#1a1a2e", "#2ecc71"]
```

The manifest declares theme metadata. Token maps (the actual CSS custom property overrides) are registered in `__init__.py` via `ctx.register_contribution("theme", ...)` because TOML isn't ideal for large key-value maps:

```python
MYAPP_DARK_TOKENS = {
    "--continuum-bg-primary": "#1a1a2e",
    "--continuum-bg-secondary": "#16213e",
    "--continuum-bg-tertiary": "#1e2a4a",
    "--continuum-bg-hover": "#2a3a5a",
    "--continuum-bg-active": "#e945601a",
    "--continuum-border": "#2a3a5a",
    "--continuum-border-muted": "#1e2a4a",
    "--continuum-text-primary": "#e0e0e0",
    "--continuum-text-secondary": "#a0a0b0",
    "--continuum-text-muted": "#707080",
    "--continuum-text-link": "#e94560",
    "--continuum-accent-primary": "#e94560",
    "--continuum-accent-success": "#2ecc71",
    "--continuum-accent-warning": "#f39c12",
    "--continuum-accent-danger": "#e74c3c",
    "--continuum-shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.3)",
    "--continuum-shadow-md": "0 4px 12px rgba(0, 0, 0, 0.4)",
    "--continuum-shadow-lg": "0 8px 24px rgba(0, 0, 0, 0.5)",
}

def register(ctx):
    ctx.register_contribution("theme", {
        "id": "myapp-dark",
        "tokens": MYAPP_DARK_TOKENS,
    })
```

**Notes:**
- Themes contributed by plugins appear in the footer selector automatically alongside the built-in themes (Default Dark, Light, High Contrast)
- Contributing a theme with the same ID as a built-in (e.g., `id = "light"`) overrides the built-in version
- The `preview_colors` list provides 5 representative hex colors used for swatch display in the selector
- See the [CSS Variables](#css-variables) section for the full list of available tokens

## Python Entrypoint

Every plugin needs an `__init__.py` with a `register` function:

```python
"""My Plugin - Description of what it does."""


def register(ctx):
    """Register plugin contributions."""
    # Register a panel
    ctx.register_contribution("panel", {
        "slot": "ui.slot.main",
        "perspective": "signal",
        "component": "my-plugin-panel",
        "priority": 100,
    })

    # Register a command
    ctx.register_contribution("command", {
        "id": "my_action",
        "label": "My Action",
        "action": "my_handler",
        "danger_level": "safe",
    })
```

The `ctx` object provides:
- `ctx.register_contribution(type, data)` - Register a contribution
- `ctx.plugin_id` - Your plugin's ID
- `ctx.discovery_index` - Order in which plugin was discovered

## UI Components (Web Components)

Plugin UIs use Svelte compiled to Web Components.

### Creating a Component

```svelte
<!-- ui/src/MyPanel.svelte -->
<svelte:options customElement="your-plugin-name-panel" />

<script lang="ts">
  import { onMount } from 'svelte';

  let data = $state([]);

  onMount(async () => {
    const res = await fetch('/api/my-endpoint');
    data = await res.json();
  });
</script>

<div class="panel">
  <h3>My Panel</h3>
  <!-- Your content -->
</div>

<style>
  .panel {
    background: var(--continuum-bg-secondary);
    border-radius: var(--continuum-radius-md);
    padding: var(--continuum-space-md);
  }
</style>
```

**Important:** The `customElement` name MUST match your `tag_prefix` plus a suffix.

### Vite Configuration

```javascript
// ui/vite.config.js
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  build: {
    lib: {
      entry: 'src/index.js',
      formats: ['es'],
      fileName: 'plugin'
    },
    outDir: '../dist'
  },
  plugins: [
    svelte({
      compilerOptions: { customElement: true }
    })
  ]
});
```

### Index Entry Point

```javascript
// ui/src/index.js
import './MyPanel.svelte';
import './MyDrawer.svelte';
// Import all components to ensure they're bundled
```

### Building

```bash
cd plugins/your.plugin_name/ui
npm install
npm run build  # Outputs to ../dist/plugin.js
```

Or use the project-wide build script:
```bash
./scripts/build-plugins.sh
```

## Available Slots

| Slot ID | Cardinality | Description |
|---------|-------------|-------------|
| `ui.slot.left_nav` | MANY | Navigation bar (perspective switcher, action triggers) |
| `ui.slot.header` | ONE | Top header (title, search, user profile) |
| `ui.slot.main` | MANY | Primary content area (perspective-scoped panels) |
| `ui.slot.right_rail` | MANY | Secondary panels (activity feeds, lists) |
| `ui.slot.footer` | ONE | Status bar, system info |
| `ui.slot.modal` | MANY | Overlay dialogs (command palette, confirmations) |
| `ui.slot.drawer` | MANY | Slide-in panels (agent chat, detail views) |
| `ui.slot.toast_stack` | MANY | Transient notifications |

## CSS Variables

Use these CSS variables for consistent theming:

```css
/* Backgrounds */
var(--continuum-bg-primary)
var(--continuum-bg-secondary)
var(--continuum-bg-tertiary)
var(--continuum-bg-hover)

/* Text */
var(--continuum-text-primary)
var(--continuum-text-secondary)
var(--continuum-text-muted)

/* Accents */
var(--continuum-accent-primary)
var(--continuum-accent-success)
var(--continuum-accent-warning)
var(--continuum-accent-danger)

/* Borders & Spacing */
var(--continuum-border)
var(--continuum-radius-sm)
var(--continuum-radius-md)
var(--continuum-space-xs)
var(--continuum-space-sm)
var(--continuum-space-md)
var(--continuum-space-lg)

/* Typography */
var(--continuum-font-sans)
var(--continuum-font-mono)
var(--continuum-font-size-xs)
var(--continuum-font-size-sm)
var(--continuum-font-size-md)
```

## Local Development

1. Create your plugin directory:
   ```bash
   mkdir -p plugins/my.plugin
   ```

2. Add `plugin.toml` and `__init__.py`

3. Restart the Continuum server to discover your plugin:
   ```bash
   # The server must be restarted for plugin discovery
   continuum serve
   ```

4. For UI development, build your components:
   ```bash
   cd plugins/my.plugin/ui
   npm run build
   ```

5. Refresh the browser to load your updated bundle

## Plugin Discovery Rules

- Plugins are discovered in **alphabetical order** by directory name
- The `discovery_index` determines priority tie-breaking
- Required plugins (`required = true`) cause DEGRADED state if they fail
- Optional plugins (`required = false`) only produce warnings if they fail

## Complete Example

See the sample plugins for full working examples:
- `plugins/continuum.sample_nav/` - Navigation contributions
- `plugins/continuum.sample_signal/` - Panel contributions with UI
- `plugins/continuum.sample_command/` - Command contributions
- `plugins/continuum.sample_chat/` - Drawer contribution
- `plugins/continuum.sample_systems/` - Complex multi-panel plugin
