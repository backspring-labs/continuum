# Plan: Dynamic Plugin UI Loading

## Overview

Replace the static component registry hack with proper Web Components-based plugin loading. After this work, M2 will be architecturally complete and we can resume the original V1 plan (M3: Command Execution, M4: Polish & Production).

## End State Definition

> Drop a new plugin folder (manifest + dist bundle), restart server, refresh browser → new panel renders.
> No shell code changes, no shell rebuild, no component registry.

## Current State (The Hack)

```
web/src/lib/components/plugins/index.ts  <-- imports all plugin Svelte components
web/src/lib/components/plugins/*.svelte  <-- plugin UI compiled into shell
web/src/lib/components/RegionSlot.svelte <-- uses getComponent() static lookup
```

Shell has compile-time dependency on plugin UI code. This breaks the plugin model.

## Target State

```
plugins/{id}/ui/src/*.svelte     <-- plugin UI source (Svelte with customElement option)
plugins/{id}/dist/plugin.js      <-- built Web Component bundle
GET /plugins/{id}/assets/plugin.js?v={hash}  <-- served by FastAPI with cache-busting
Shell injects <script>, renders <custom-element-tag />
```

Zero compile-time coupling. Plugins can be added without rebuilding shell.

---

## Phase 1: Remove the Hack (Task A)

**Files to delete:**
- `web/src/lib/components/plugins/index.ts`
- `web/src/lib/components/plugins/*.svelte` (all 7 files)

**Files to modify:**
- `web/src/lib/components/RegionSlot.svelte` - Remove `getComponent` import, use placeholder for all contributions temporarily

**Verification:** Shell compiles and runs with no plugin UI imports. All panels show placeholders.

---

## Phase 2: Plugin Build Infrastructure (Tasks B, C)

### B) Manifest Contract (Minimal)

Update `plugins/*/plugin.toml`:

```toml
[plugin]
id = "continuum.sample_signal"
name = "Signal Dashboard"
version = "1.0.0"

[plugin.ui]
bundle = "plugin.js"  # filename only; server knows dist/ is the convention

[[contributions.panel]]
slot = "ui.slot.main"
perspective = "signal"
component = "continuum-sample-signal-metrics"  # custom element tag
priority = 200
```

**Contract is minimal:**
- `bundle` - filename of built bundle (server serves from `dist/` by convention)
- `component` - custom element tag to render (in contributions)
- No `tag_prefix` in domain model (naming conventions enforced via build/lint only)

Update `src/continuum/domain/manifest.py` to parse `bundle` field under `plugin.ui`.

**Bundle validation during discovery:**
```python
# In manifest parser or loader
bundle = ui_config.get("bundle", "")
if not bundle:
    pass  # No UI bundle, that's fine
elif bundle.endswith("/") or ":" in bundle or "\\" in bundle:
    raise ManifestError(f"Invalid bundle path: {bundle}")
```

### C) Plugin Build Setup

Create plugin UI build infrastructure:

```
plugins/continuum.sample_signal/
  ui/
    src/
      SignalMetrics.svelte    # <svelte:options customElement="..." />
      SignalTimeline.svelte
      SignalAlerts.svelte
      index.js                # imports all components (triggers registration)
  dist/
    plugin.js                 # output: registers custom elements
  plugin.toml
```

**Shared build script:** `scripts/build-plugins.js`
- Discovers plugins with `ui/` directory
- Uses shared Vite config template with per-plugin entry points
- Outputs to `plugins/{id}/dist/plugin.js`
- Avoids per-plugin vite.config.js duplication

**Svelte custom element pattern:**
```svelte
<svelte:options customElement="continuum-sample-signal-metrics" />
<script>
  // component logic
</script>
<div class="panel">...</div>
<style>
  /* styles are encapsulated in shadow DOM */
</style>
```

**Plugin entry point (`ui/src/index.js`):**
```js
// Just importing registers the custom elements
import './SignalMetrics.svelte';
import './SignalTimeline.svelte';
import './SignalAlerts.svelte';
```

**Verification:** Running `node scripts/build-plugins.js` produces `dist/plugin.js` for each plugin.

---

## Phase 3: Backend Asset Serving (Task D)

### Path Alignment (Critical)

Align manifest, registry, and endpoint consistently:

| Layer | Value | Example |
|-------|-------|---------|
| Manifest | `bundle = "plugin.js"` | just filename, no `dist/` prefix |
| Server knows | dist dir is `plugins/{id}/dist/` | hardcoded convention |
| Registry URL | `/plugins/{id}/assets/{bundle}?v={ver}` | uses manifest bundle value |
| Endpoint | serves from `{plugin.directory}/dist/{path}` | path = manifest bundle |

**File:** `src/continuum/adapters/web/api.py`

Add endpoint with robust path traversal defense:

```python
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

@router.get("/plugins/{plugin_id}/assets/{path:path}")
async def plugin_assets(plugin_id: str, path: str, request: Request):
    runtime = request.app.state.runtime

    # Validate plugin exists
    plugin = runtime.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(404, f"Plugin not found: {plugin_id}")

    # Reject obviously invalid paths
    if not path or path.startswith("/") or "\\" in path:
        raise HTTPException(400, "Invalid path")

    # Resolve and validate path stays within dist directory
    dist_dir = (Path(plugin.directory) / "dist").resolve()
    asset_path = (dist_dir / path).resolve()

    # Prevent traversal: resolved path must be under dist_dir
    try:
        asset_path.relative_to(dist_dir)
    except ValueError:
        raise HTTPException(400, "Invalid path")

    if not asset_path.is_file():
        raise HTTPException(404, f"Asset not found: {path}")

    # Serve with dev-friendly cache headers
    return FileResponse(
        asset_path,
        headers={"Cache-Control": "no-store"}  # Dev mode; add caching in prod
    )
```

**Update registry response** - use manifest's bundle path (not hardcoded):

```python
class RegistryResponse(BaseModel):
    # ... existing fields ...
    plugin_bundles: dict[str, str]  # plugin_id -> bundle_url with cache-bust

# In registry endpoint:
plugin_bundles = {}
for plugin in runtime.plugins:
    if plugin.ui_bundle:
        # Validate bundle path is safe (no traversal)
        bundle_path = plugin.ui_bundle  # e.g., "plugin.js" from manifest
        if ".." in bundle_path or bundle_path.startswith("/") or "\\" in bundle_path:
            runtime.add_warning(f"Plugin {plugin.id} has invalid bundle path: {bundle_path}")
            continue

        # Cache-bust with version or mtime
        version = plugin.version or str(plugin.bundle_mtime)
        plugin_bundles[plugin.id] = f"/plugins/{plugin.id}/assets/{bundle_path}?v={version}"

return RegistryResponse(
    # ...
    plugin_bundles=plugin_bundles,
)
```

**Validation during discovery** (in registry.py):
```python
# Validate contributions reference known plugins and have valid component tags
for contribution in contributions:
    if contribution.plugin_id not in known_plugin_ids:
        raise RegistryError(f"Contribution references unknown plugin: {contribution.plugin_id}")
    if contribution.component and not contribution.component.strip():
        raise RegistryError(f"Contribution has empty component tag: {contribution}")
```

**Verification:**
- `curl http://localhost:4040/plugins/continuum.sample_signal/assets/plugin.js` returns JS bundle
- `curl http://localhost:4040/plugins/foo/assets/../../../etc/passwd` returns 400
- `curl http://localhost:4040/plugins/foo/assets/..%2F..%2Fetc/passwd` returns 400 (URL-encoded)
- `/api/registry` includes `plugin_bundles` map using manifest bundle paths with cache-bust

---

## Phase 4: Shell Runtime Loader (Task E)

**New file:** `web/src/lib/services/pluginLoader.ts`

```typescript
type LoadState = 'pending' | 'loading' | 'ready' | 'failed';

// Track loaded bundles and their states
const loadedBundles = new Set<string>();
const bundleStates = new Map<string, LoadState>();
const bundleErrors = new Map<string, string>();

// Concurrency-safe: shared promises for in-flight loads
const inflight = new Map<string, Promise<void>>();

export async function loadBundle(url: string): Promise<void> {
  // Key by full URL including ?v= query string.
  // This means version changes trigger new loads (intentional across deployments).
  // Within a single session, the registry returns stable URLs, so no double-loads.

  // Already loaded
  if (loadedBundles.has(url)) return;

  // Already loading - return existing promise
  if (inflight.has(url)) {
    return inflight.get(url)!;
  }

  // Start new load
  bundleStates.set(url, 'loading');

  const promise = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.type = 'module';
    script.src = url;

    script.onload = () => {
      loadedBundles.add(url);
      bundleStates.set(url, 'ready');
      inflight.delete(url);
      resolve();
    };

    script.onerror = () => {
      const error = `Failed to load bundle: ${url}`;
      bundleStates.set(url, 'failed');
      bundleErrors.set(url, error);
      inflight.delete(url);
      reject(new Error(error));
    };

    document.head.appendChild(script);
  });

  inflight.set(url, promise);
  return promise;
}

export function getBundleState(url: string): LoadState {
  return bundleStates.get(url) ?? 'pending';
}

export function getBundleError(url: string): string | undefined {
  return bundleErrors.get(url);
}

// Wait for custom element with timeout
const ELEMENT_TIMEOUT_MS = 5000;

export async function waitForElement(tag: string): Promise<void> {
  const timeout = new Promise<never>((_, reject) => {
    setTimeout(() => {
      reject(new Error(`Bundle loaded but <${tag}> was not registered after ${ELEMENT_TIMEOUT_MS}ms`));
    }, ELEMENT_TIMEOUT_MS);
  });

  return Promise.race([
    customElements.whenDefined(tag),
    timeout
  ]);
}
```

**Update:** `web/src/lib/stores/registry.ts`

```typescript
// Add to Contribution type (no bundle_url - resolved from plugin_bundles)
// Add plugin_bundles to registry state

export interface Registry {
  // ... existing ...
  plugin_bundles: Record<string, string>;  // plugin_id -> bundle_url
}

// Helper to get bundle URL for a contribution
export function getBundleUrl(contribution: Contribution, registry: Registry): string | undefined {
  return registry.plugin_bundles[contribution.plugin_id];
}
```

**Update:** `web/src/lib/components/RegionSlot.svelte`

```svelte
<script lang="ts">
  import { loadBundle } from '$lib/services/pluginLoader';
  import { registry, getBundleUrl } from '$stores/registry';
  import ComponentLoader from './ComponentLoader.svelte';
  import type { Contribution } from '$stores/registry';

  interface Props {
    slotId: string;
    contributions: Contribution[];
  }

  let { slotId, contributions }: Props = $props();

  // Compute unique bundles needed and load them.
  // Effect only re-runs when contributions or registry changes meaningfully.
  // loadBundle is idempotent (returns immediately if already loaded/loading).
  $effect(() => {
    const bundles = new Set<string>();
    for (const c of contributions) {
      const url = getBundleUrl(c, $registry);
      if (url) bundles.add(url);
    }
    bundles.forEach(url => loadBundle(url).catch(() => {}));  // errors handled in ComponentLoader
  });
</script>

<div class="region-slot" data-slot={slotId}>
  {#each contributions as contribution (contribution.plugin_id + '-' + contribution.component)}
    <ComponentLoader {contribution} bundleUrl={getBundleUrl(contribution, $registry)} />
  {/each}

  {#if contributions.length === 0}
    <div class="empty-slot">
      <span class="empty-label">No contributions for {slotId}</span>
    </div>
  {/if}
</div>

<style>
  /* ... existing styles ... */
</style>
```

**New file:** `web/src/lib/components/ComponentLoader.svelte`

```svelte
<script lang="ts">
  import { getBundleState, getBundleError, waitForElement } from '$lib/services/pluginLoader';
  import type { Contribution } from '$stores/registry';

  interface Props {
    contribution: Contribution;
    bundleUrl: string | undefined;
  }

  let { contribution, bundleUrl }: Props = $props();

  let bundleState = $derived(bundleUrl ? getBundleState(bundleUrl) : 'failed');
  let bundleError = $derived(bundleUrl ? getBundleError(bundleUrl) : 'No bundle URL');
  let elementReady = $state(false);
  let elementError = $state<string | null>(null);

  $effect(() => {
    if (bundleState === 'ready' && contribution.component) {
      waitForElement(contribution.component)
        .then(() => { elementReady = true; })
        .catch((err) => { elementError = err.message; });
    }
  });
</script>

{#if !bundleUrl}
  <div class="panel-error">
    <strong>No bundle configured</strong>
    <dl>
      <dt>Plugin</dt><dd>{contribution.plugin_id}</dd>
      <dt>Component</dt><dd>{contribution.component}</dd>
    </dl>
  </div>
{:else if bundleState === 'loading'}
  <div class="panel-loading">
    <span class="spinner"></span>
    Loading {contribution.component}...
  </div>
{:else if bundleState === 'failed'}
  <div class="panel-error">
    <strong>Failed to load plugin bundle</strong>
    <dl>
      <dt>Plugin</dt><dd>{contribution.plugin_id}</dd>
      <dt>Component</dt><dd>{contribution.component}</dd>
      <dt>Bundle</dt><dd>{bundleUrl}</dd>
      <dt>Error</dt><dd>{bundleError}</dd>
    </dl>
  </div>
{:else if elementError}
  <div class="panel-error">
    <strong>Component not registered</strong>
    <dl>
      <dt>Plugin</dt><dd>{contribution.plugin_id}</dd>
      <dt>Component</dt><dd>{contribution.component}</dd>
      <dt>Bundle</dt><dd>{bundleUrl}</dd>
      <dt>Error</dt><dd>{elementError}</dd>
    </dl>
  </div>
{:else if elementReady}
  <div class="contribution" data-plugin={contribution.plugin_id}>
    <svelte:element this={contribution.component} />
  </div>
{:else}
  <div class="panel-loading">
    <span class="spinner"></span>
    Initializing {contribution.component}...
  </div>
{/if}

<style>
  .panel-loading {
    display: flex;
    align-items: center;
    gap: var(--continuum-space-sm);
    padding: var(--continuum-space-lg);
    background: var(--continuum-bg-secondary);
    border-radius: var(--continuum-radius-md);
    color: var(--continuum-text-secondary);
  }

  .panel-error {
    padding: var(--continuum-space-md);
    background: rgba(248, 81, 73, 0.1);
    border: 1px solid var(--continuum-accent-danger);
    border-radius: var(--continuum-radius-md);
    color: var(--continuum-text-primary);
  }

  .panel-error strong {
    color: var(--continuum-accent-danger);
  }

  .panel-error dl {
    margin: var(--continuum-space-sm) 0 0;
    font-size: var(--continuum-font-size-sm);
  }

  .panel-error dt {
    font-weight: 600;
    color: var(--continuum-text-secondary);
  }

  .panel-error dd {
    margin: 0 0 var(--continuum-space-xs);
    font-family: var(--continuum-font-mono);
    word-break: break-all;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--continuum-border);
    border-top-color: var(--continuum-accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .contribution {
    display: block;
  }
</style>
```

**Verification:**
- Switching perspectives loads only required bundles (check Network tab)
- Same bundle is never loaded twice (check Network tab, console)
- Custom elements render in their slots
- Failed bundle shows error panel with plugin_id, component, bundle_url, error
- Bundle loads but missing element shows "Component not registered" after 5s timeout

---

## Phase 5: Guardrails & Tests (Task F)

### Compile-time coupling guard (expanded)

**File:** `scripts/check-plugin-coupling.sh`

```bash
#!/bin/bash
set -e

echo "Checking for plugin UI coupling in shell..."

# Check for any imports from plugins directory
if grep -rE "(from|import).*['\"].*plugins/" web/src/ --include="*.ts" --include="*.svelte" --include="*.js" 2>/dev/null; then
  echo ""
  echo "ERROR: Shell has compile-time imports from plugins directory"
  echo "The shell must not import plugin UI source code."
  exit 1
fi

# Check for any relative imports that could reach plugins
if grep -rE "from ['\"]\.\.\/\.\.\/.*plugins" web/src/ --include="*.ts" --include="*.svelte" --include="*.js" 2>/dev/null; then
  echo ""
  echo "ERROR: Shell has relative imports reaching plugins directory"
  exit 1
fi

echo "OK: No plugin coupling detected in shell build graph"
```

Add to CI / pre-commit.

### Smoke tests (HTTP-level first, E2E later)

**File:** `tests/test_plugin_loading.py`

```python
import requests

BASE_URL = "http://localhost:4040"


def test_registry_includes_plugin_bundles():
    """Registry response includes plugin_bundles map with cache-busted URLs."""
    r = requests.get(f"{BASE_URL}/api/registry")
    assert r.status_code == 200
    data = r.json()

    assert "plugin_bundles" in data
    bundles = data["plugin_bundles"]

    # Check sample plugin has bundle URL
    assert "continuum.sample_signal" in bundles
    url = bundles["continuum.sample_signal"]
    assert url.startswith("/plugins/continuum.sample_signal/assets/")
    assert "?v=" in url  # cache-busting


def test_plugin_bundle_served():
    """Plugin JS bundle is served from assets endpoint."""
    r = requests.get(f"{BASE_URL}/plugins/continuum.sample_signal/assets/plugin.js")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/javascript") or \
           r.headers.get("content-type", "").startswith("text/javascript")
    assert "customElements.define" in r.text or "customElement" in r.text


def test_path_traversal_blocked():
    """Path traversal attempts are rejected."""
    r = requests.get(f"{BASE_URL}/plugins/continuum.sample_signal/assets/../../../etc/passwd")
    assert r.status_code == 400


def test_path_traversal_url_encoded():
    """URL-encoded path traversal attempts are also rejected."""
    r = requests.get(f"{BASE_URL}/plugins/continuum.sample_signal/assets/..%2F..%2F..%2Fetc/passwd")
    assert r.status_code == 400


def test_missing_plugin_404():
    """Non-existent plugin returns 404."""
    r = requests.get(f"{BASE_URL}/plugins/nonexistent.plugin/assets/plugin.js")
    assert r.status_code == 404


def test_missing_asset_404():
    """Non-existent asset returns 404."""
    r = requests.get(f"{BASE_URL}/plugins/continuum.sample_signal/assets/nonexistent.js")
    assert r.status_code == 404


def test_registry_uses_manifest_bundle_path():
    """Registry bundle URL uses the manifest's bundle field, not hardcoded plugin.js."""
    # This test catches drift between plugin builds and server routing
    r = requests.get(f"{BASE_URL}/api/registry")
    data = r.json()

    # Get the bundle URL for sample_signal
    bundle_url = data["plugin_bundles"].get("continuum.sample_signal", "")

    # Should contain the bundle filename from manifest (e.g., plugin.js)
    # NOT a hardcoded assumption
    assert "/assets/" in bundle_url
    assert "?v=" in bundle_url

    # Verify we can actually fetch it
    # Strip query string for fetch
    asset_path = bundle_url.split("?")[0]
    r2 = requests.get(f"{BASE_URL}{asset_path}")
    assert r2.status_code == 200
```

**E2E test (when Playwright is ready):**

```python
def test_custom_element_renders(page):
    """Custom element appears in DOM after shell loads."""
    page.goto("http://localhost:5173")

    # Wait for signal perspective to be active (default)
    page.wait_for_selector("[data-slot='ui.slot.main']")

    # Wait for custom element to appear
    element = page.wait_for_selector("continuum-sample-signal-metrics", timeout=10000)
    assert element is not None

    # Verify it rendered something (has shadow DOM content or inner content)
    # This confirms the web component actually executed
```

**Verification:** All tests pass.

---

## Phase 6: Documentation (Task deliverable 2)

**File:** `docs/plugin-ui-development.md`

Contents:

```markdown
# Plugin UI Development

## Overview

Continuum plugins can contribute UI components that render in the shell.
UI plugins ship built Web Component bundles that are loaded at runtime.

## Key Principles

1. **Server restart required** - Plugin discovery happens at server start.
   After adding a plugin, restart the server and refresh the browser.

2. **Zero shell coupling** - The shell never imports plugin UI source code.
   Plugins are loaded dynamically via `<script>` injection.

3. **Web Components boundary** - Plugin UI components are custom elements.
   They register themselves via `customElements.define()`.

## Plugin Structure

```
plugins/my.plugin/
  plugin.toml          # Manifest declaring bundle + contributions
  ui/
    src/
      MyPanel.svelte   # Svelte component with customElement option
      index.js         # Entry point that imports all components
  dist/
    plugin.js          # Built bundle (committed or CI-generated)
```

## Manifest Contract

```toml
[plugin]
id = "my.plugin"
name = "My Plugin"
version = "1.0.0"

[plugin.ui]
bundle = "plugin.js"   # Bundle filename (served from dist/ by convention)

[[contributions.panel]]
slot = "ui.slot.main"
perspective = "signal"
component = "my-plugin-panel"   # Custom element tag name
priority = 100
```

## Creating a Component

Use Svelte's `customElement` option:

```svelte
<svelte:options customElement="my-plugin-panel" />

<script>
  // Your component logic
</script>

<div class="panel">
  <h2>My Panel</h2>
  <p>Content here</p>
</div>

<style>
  /* Styles are encapsulated in shadow DOM */
  .panel {
    padding: 16px;
    background: var(--continuum-bg-secondary);
  }
</style>
```

## Entry Point

Create `ui/src/index.js` that imports all components:

```js
// Importing registers the custom elements
import './MyPanel.svelte';
import './MyOtherPanel.svelte';
```

## Building

Run the shared build script:

```bash
node scripts/build-plugins.js
```

Or build a specific plugin:

```bash
node scripts/build-plugins.js --plugin my.plugin
```

Output: `plugins/my.plugin/dist/plugin.js`

## How Loading Works

1. Shell fetches `/api/registry` which includes `plugin_bundles` map
2. For active perspective, shell determines which bundles are needed
3. Shell injects `<script type="module" src="...">` for each bundle (once)
4. Bundle executes, registering custom elements via `customElements.define()`
5. Shell renders `<my-plugin-panel />` in the appropriate region slot
6. Browser instantiates the custom element

## Debugging

### Component not appearing

1. Check Network tab - is the bundle loading? (200 status)
2. Check Console - any errors during bundle execution?
3. Verify `customElements.define()` is called with correct tag name
4. Verify contribution's `component` matches the tag name exactly

### "Component not registered" error

The bundle loaded but didn't register the expected custom element tag.

- Check that component has `<svelte:options customElement="exact-tag-name" />`
- Check that `index.js` imports the component
- Check for typos between manifest `component` and Svelte `customElement`

### Stale code after changes

Bundles are cache-busted with `?v=<version>`. If you see old code:

1. Did you rebuild? `node scripts/build-plugins.js`
2. Did you update `version` in `plugin.toml`?
3. Hard refresh: Cmd+Shift+R / Ctrl+Shift+R
```

---

## Implementation Order

```
Phase 1 (A)     Remove hack, shell compiles clean
Phase 2 (B+C)   Manifest contract + plugin build infra
Phase 3 (D)     Backend asset serving + cache-busting
Phase 4 (E)     Shell runtime loader + renderer
Phase 5 (F)     Guardrails + tests
Phase 6         Documentation
```

---

## Resuming Original V1 Plan

After this work completes:

| Milestone | Status | Description |
|-----------|--------|-------------|
| M0: Shell Boot | Done | FastAPI + SvelteKit |
| M1: Plugin Runtime | Done | Discovery, manifests, registry |
| M2: UI Rendering | **Done after this plan** | Dynamic Web Component loading |
| M3: Command Execution | Next | Wire up command palette, keyboard shortcuts |
| M4: Polish & Production | Final | Build pipeline, static serving, error boundaries |

M3 and M4 remain unchanged. This plan fixes the M2 architectural gap.

---

## Files Modified/Created Summary

**Delete:**
- `web/src/lib/components/plugins/` (entire directory)

**Modify:**
- `plugins/*/plugin.toml` (add `bundle` field, remove `tag_prefix` if present)
- `src/continuum/domain/manifest.py` (parse `ui.bundle`)
- `src/continuum/adapters/web/api.py` (add assets endpoint, add `plugin_bundles` to registry)
- `src/continuum/app/registry.py` (compute bundle URLs with cache-busting)
- `web/src/lib/components/RegionSlot.svelte` (use runtime loader)
- `web/src/lib/stores/registry.ts` (add `plugin_bundles`, helper function)

**Create:**
- `plugins/*/ui/src/*.svelte` (plugin UI source with customElement)
- `plugins/*/ui/src/index.js` (entry point)
- `scripts/build-plugins.js` (shared build script)
- `web/src/lib/services/pluginLoader.ts` (runtime bundle loader)
- `web/src/lib/components/ComponentLoader.svelte` (loading states + error display)
- `scripts/check-plugin-coupling.sh` (coupling guard)
- `tests/test_plugin_loading.py` (HTTP + E2E tests)
- `docs/plugin-ui-development.md` (developer guide)

---

## Verification Checklist

- [ ] Shell compiles with zero imports from `plugins/`
- [ ] `scripts/check-plugin-coupling.sh` passes
- [ ] `node scripts/build-plugins.js` produces `dist/plugin.js` for each plugin
- [ ] `GET /plugins/{id}/assets/plugin.js` returns bundle with correct Content-Type
- [ ] Path traversal attempts return 400 (including URL-encoded variants)
- [ ] `/api/registry` includes `plugin_bundles` map using manifest bundle paths
- [ ] Registry validates contributions reference known plugin IDs
- [ ] Same bundle URL is never loaded twice (concurrent-safe)
- [ ] Switching perspectives loads only required bundles
- [ ] Custom elements render in correct slots
- [ ] Failed bundle shows error panel with plugin_id, component, bundle_url, error
- [ ] Missing element registration shows "Component not registered" after 5s timeout
- [ ] All smoke tests pass (including manifest bundle path test)
- [ ] Documentation is complete
