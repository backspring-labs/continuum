# RCA-001: Plugin Component Loading Architecture Violation

**Date:** 2025-02-05
**Status:** Open - Blocking M2 completion
**Severity:** Critical - Breaks core plugin architecture

## Summary

The current implementation hardwires plugin UI components into the shell's source code, violating the fundamental requirement that plugins contribute UI without modifying the shell. This was introduced as a workaround for Web Components compilation issues with SvelteKit 5 and should have been flagged as a blocking issue rather than accepted as a "pragmatic shortcut."

## Intended Architecture

Continuum is designed as a plugin-driven control plane where:

1. Plugins are discovered at runtime from the `plugins/` directory
2. Each plugin declares UI contributions in its `plugin.toml` manifest
3. The shell dynamically loads and renders plugin components by name
4. Adding a new plugin requires **zero changes** to the shell source

Example from a plugin manifest:
```toml
[[contributions.panel]]
slot = "ui.slot.main"
perspective = "signal"
component = "continuum-sample-signal-metrics"
priority = 200
```

The shell should resolve `continuum-sample-signal-metrics` to actual rendered UI at runtime, without compile-time knowledge of what plugins exist.

## Initial Approach: Web Components

The original plan was to use Web Components (Custom Elements) for plugin UI:

1. Each plugin compiles its Svelte components to custom elements
2. Plugin assets (JS bundles) are served by the FastAPI backend
3. The shell loads `<script>` tags for active plugins
4. Components render via their custom element tags: `<continuum-sample-signal-metrics />`

This approach is framework-agnostic and follows established patterns (VS Code webviews, Figma plugins, etc.).

## The Problem Encountered

When implementing Web Components with SvelteKit 5, we hit compilation conflicts:

### Issue 1: Dual Compilation Modes

Svelte components can be compiled in two modes:
- **Standard mode:** For use within a Svelte app
- **Custom Element mode:** For use as Web Components (`customElement: true`)

SvelteKit's `vite-plugin-svelte` is configured for standard mode. Adding a second `svelte()` plugin instance for custom element compilation caused conflicts:

```
Error: Multiple Svelte plugins detected
```

### Issue 2: The `<svelte:options>` Tag

Svelte 5 requires components to declare custom element intent via:
```svelte
<svelte:options customElement="my-component" />
```

But components with this option cannot be imported normally within the SvelteKit app - they're only usable as custom elements. This creates a split where:
- Shell components must NOT have `customElement` option
- Plugin components must HAVE `customElement` option
- They cannot coexist in the same compilation pipeline

### Issue 3: Separate Build Pipeline Complexity

The "proper" solution requires:
1. A separate Vite config for plugin compilation
2. Plugins built independently to JS bundles
3. Bundles served from FastAPI
4. Dynamic `<script>` injection in the shell

This was deemed "too complex" at the time and deferred.

## The Shortcut Taken

Instead of solving dynamic loading, I created a static component registry:

```typescript
// web/src/lib/components/plugins/index.ts
export const componentRegistry: Record<string, Component> = {
  'continuum-sample-signal-metrics': SignalMetrics,
  'continuum-sample-signal-timeline': SignalTimeline,
  'continuum-sample-signal-alerts': SignalAlerts,
  // ... all plugin components hardwired here
};
```

The shell looks up components by name from this map. This "works" for demo purposes but completely breaks the architecture.

## Why This Is Critical

1. **Adding a plugin requires modifying shell code** - defeats the entire plugin model
2. **Compile-time coupling** - shell must import every plugin component
3. **No third-party plugins** - external developers cannot add plugins
4. **Not a plugin system** - it's a monolith with extra indirection
5. **Registry becomes meaningless** - if we hardwire components, why have manifests?

## Options to Evaluate

### Option A: Fix Web Components with Separate Build

- Create `plugins/build.js` script that compiles each plugin to a custom element bundle
- Serve bundles from FastAPI at `/plugins/{id}/assets/`
- Shell injects `<script>` tags and uses custom element tags
- **Pro:** Framework-agnostic, proven pattern
- **Con:** Build complexity, two compilation pipelines

### Option B: Dynamic Import via Plugin URLs

- Plugins export ES modules (not custom elements)
- Shell uses `import()` to dynamically load from plugin asset URLs
- Requires careful module format handling
- **Pro:** Simpler than Web Components
- **Con:** Still Svelte-coupled, CORS/bundling challenges

### Option C: iframe Isolation

- Each plugin panel is an iframe
- Plugins serve their own HTML/JS/CSS
- Communication via postMessage
- **Pro:** Complete isolation, any framework per plugin
- **Con:** Performance overhead, complex state sharing

### Option D: Switch to React

- React has more mature dynamic loading patterns
- `React.lazy()` + Suspense for code splitting
- Module Federation (Webpack 5) is well-documented
- **Pro:** Larger ecosystem, more examples of plugin architectures
- **Con:** Rewrite cost, team familiarity

### Option E: Svelte + Module Federation

- Use `@originjs/vite-plugin-federation` for Vite
- Plugins are "remote" modules loaded at runtime
- Shell is the "host" that consumes them
- **Pro:** Keeps Svelte, designed for this use case
- **Con:** Less mature than Webpack Module Federation

## Questions for Outside Counsel

1. Is Web Components the right abstraction for plugin UI, or is it overengineering?
2. Does Svelte's compilation model fundamentally conflict with dynamic plugin loading?
3. Is Module Federation mature enough in the Vite ecosystem?
4. What do comparable systems (Backstage, Grafana, VS Code) use for plugin UI?
5. Is the React ecosystem's maturity worth a framework switch at this stage?

## Current State

- **Backend:** Working correctly - discovers plugins, parses manifests, serves registry
- **Frontend:** Architecturally broken - hardwired components in `web/src/lib/components/plugins/`
- **Tests:** 24 passing, but testing the wrong abstraction

## Files Involved

- `web/src/lib/components/plugins/index.ts` - The hardwired registry (the hack)
- `web/src/lib/components/RegionSlot.svelte` - Uses `getComponent()` to resolve
- `plugins/*/plugin.toml` - Declare component names that should load dynamically
- `web/vite.config.ts` - Would need modification for any solution

## Recommendation

Do not proceed to M3 until this is resolved. The current implementation is a proof-of-concept that validates the registry/contribution model but does not validate the plugin loading model. Any further work builds on a broken foundation.
