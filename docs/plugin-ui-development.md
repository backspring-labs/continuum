# Plugin UI Development Guide

This guide explains how to create UI components for Continuum plugins using Web Components.

## Overview

Plugin UI in Continuum is built using Svelte components that compile to Web Components (Custom Elements). This approach provides:

- **Zero compile-time coupling**: The shell doesn't import plugin code at build time
- **Dynamic loading**: Plugin UIs load on-demand when needed
- **Style isolation**: Shadow DOM encapsulates component styles
- **Framework flexibility**: Plugins can use any framework that compiles to Web Components

## Architecture

```
plugins/{plugin_id}/
  plugin.toml          # Plugin manifest with bundle path
  __init__.py          # Python entrypoint
  ui/
    src/
      Component.svelte # Svelte components with customElement option
      index.js         # Entry point that imports all components
    vite.config.js     # Build configuration
    package.json       # Dependencies
  dist/
    plugin.js          # Built Web Component bundle
```

## Quick Start

### 1. Add Bundle Path to Manifest

In your `plugin.toml`, add the `bundle` field to the `[plugin.ui]` section:

```toml
[plugin.ui]
tag_prefix = "my-plugin"
bundle = "plugin.js"
```

The `bundle` field is the filename within the `dist/` directory (not the full path).

### 2. Create the UI Directory Structure

```bash
mkdir -p plugins/my.plugin/ui/src
mkdir -p plugins/my.plugin/dist
```

### 3. Create a Svelte Component

Create a component with the `customElement` option in `ui/src/MyPanel.svelte`:

```svelte
<svelte:options customElement="my-plugin-panel" />

<script lang="ts">
  import { onMount } from 'svelte';

  let data = $state([]);

  onMount(async () => {
    const res = await fetch('/api/my-data');
    data = await res.json();
  });
</script>

<div class="panel">
  <h3>My Panel</h3>
  <ul>
    {#each data as item}
      <li>{item.name}</li>
    {/each}
  </ul>
</div>

<style>
  .panel {
    background: var(--continuum-bg-secondary, #1a1a2e);
    border: 1px solid var(--continuum-border, #2d2d44);
    border-radius: var(--continuum-radius-md, 8px);
    padding: var(--continuum-space-md, 16px);
    font-family: var(--continuum-font-sans, system-ui, sans-serif);
    color: var(--continuum-text-primary, #e8e8e8);
  }
</style>
```

### 4. Create the Entry Point

Create `ui/src/index.js`:

```javascript
// Import all components - they auto-register via customElement option
import './MyPanel.svelte';
import './MyWidget.svelte';
```

### 5. Add Build Configuration

Create `ui/package.json`:

```json
{
  "name": "@continuum/my-plugin-ui",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "vite build"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "^5.0.0",
    "svelte": "^5.0.0",
    "vite": "^6.0.0"
  }
}
```

Create `ui/vite.config.js`:

```javascript
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [
    svelte({
      compilerOptions: {
        customElement: true,
      },
    }),
  ],
  build: {
    lib: {
      entry: 'src/index.js',
      formats: ['es'],
      fileName: 'plugin',
    },
    outDir: '../dist',
    emptyOutDir: true,
  },
});
```

### 6. Build the Plugin

```bash
cd plugins/my.plugin/ui
npm install
npm run build
```

Or use the project-wide build script:

```bash
./scripts/build-plugins.sh
```

## CSS Variables

Use Continuum's CSS custom properties for consistent theming. Always provide fallback values for when running in isolation:

```css
.panel {
  /* Colors */
  background: var(--continuum-bg-secondary, #1a1a2e);
  color: var(--continuum-text-primary, #e8e8e8);
  border-color: var(--continuum-border, #2d2d44);

  /* Spacing */
  padding: var(--continuum-space-md, 16px);
  gap: var(--continuum-space-sm, 8px);

  /* Typography */
  font-family: var(--continuum-font-sans, system-ui, sans-serif);
  font-size: var(--continuum-font-size-sm, 12px);

  /* Borders */
  border-radius: var(--continuum-radius-md, 8px);
}
```

Available CSS variables:

| Category | Variables |
|----------|-----------|
| Backgrounds | `--continuum-bg-primary`, `--continuum-bg-secondary`, `--continuum-bg-tertiary`, `--continuum-bg-hover`, `--continuum-bg-active` |
| Text | `--continuum-text-primary`, `--continuum-text-secondary`, `--continuum-text-muted` |
| Accents | `--continuum-accent-primary`, `--continuum-accent-success`, `--continuum-accent-warning`, `--continuum-accent-danger` |
| Spacing | `--continuum-space-xs` (4px), `--continuum-space-sm` (8px), `--continuum-space-md` (16px), `--continuum-space-lg` (24px), `--continuum-space-xl` (32px) |
| Typography | `--continuum-font-size-xs` (11px), `--continuum-font-size-sm` (12px), `--continuum-font-size-md` (14px), `--continuum-font-size-lg` (16px), `--continuum-font-size-xl` (20px) |
| Fonts | `--continuum-font-sans`, `--continuum-font-mono` |
| Borders | `--continuum-border`, `--continuum-radius-sm` (4px), `--continuum-radius-md` (8px), `--continuum-radius-lg` (12px) |

## Custom Element Naming

The custom element tag name must:

1. Start with your plugin's `tag_prefix` from `plugin.toml`
2. Use lowercase letters and hyphens
3. Match the component attribute in your contribution

Example:
```toml
# plugin.toml
[plugin.ui]
tag_prefix = "acme-dashboard"

[[contributions.panel]]
component = "acme-dashboard-metrics"
```

```svelte
<!-- Must match -->
<svelte:options customElement="acme-dashboard-metrics" />
```

## Loading Lifecycle

When the shell needs to render a plugin component:

1. **Bundle Loading**: Shell injects a `<script type="module">` for the bundle URL
2. **Element Registration**: Bundle code runs, calling `customElements.define()`
3. **Element Ready**: Shell waits for `customElements.whenDefined()`
4. **Rendering**: Shell creates the custom element (`<my-plugin-panel />`)

During this process, users see loading indicators. If loading fails, an error panel is displayed with diagnostic information.

## Accessing APIs

Plugin components can fetch data from the Continuum API:

```javascript
// Registry data
const registry = await fetch('/api/registry').then(r => r.json());

// Diagnostics
const diagnostics = await fetch('/diagnostics').then(r => r.json());

// Health check
const health = await fetch('/health').then(r => r.json());
```

## Debugging Failed Loads

If your plugin UI fails to load, check:

1. **Bundle exists**: Verify `plugins/{id}/dist/plugin.js` was built
2. **Server running**: Test `curl http://localhost:4040/plugins/{id}/assets/plugin.js`
3. **Console errors**: Check browser devtools for JavaScript errors
4. **Element name**: Ensure the customElement name matches the contribution component
5. **Bundle syntax**: Verify the bundle compiles without errors

The error panel displayed on load failure includes:
- Plugin ID
- Component tag name
- Bundle URL
- Error message

## Server Restart Required

Plugin discovery happens at server startup. After adding a new plugin or modifying `plugin.toml`:

```bash
# Restart the FastAPI server
uvicorn continuum.adapters.web.app:app --reload
```

The `--reload` flag enables auto-restart on Python file changes, but new plugins still require a manual restart.

## Example Plugins

See the sample plugins for working examples:

- `plugins/continuum.sample_signal/` - Dashboard panels with metrics and timeline
- `plugins/continuum.sample_systems/` - Admin panels with plugin status
- `plugins/continuum.sample_chat/` - Drawer-based chat interface

## Build Script

The `scripts/build-plugins.sh` script automates building all plugin UIs:

```bash
./scripts/build-plugins.sh
```

This script:
1. Finds all plugins with `ui/` directories
2. Installs dependencies if needed
3. Runs `npm run build` for each
4. Reports build results

## Testing

Run the plugin coupling check to ensure the shell has no compile-time imports from plugins:

```bash
./scripts/check-plugin-coupling.sh
```

This should pass (exit code 0) if the architecture is correct.
