# Plan: Add React Shell to Continuum

## Context

Continuum is a plugin-driven control-plane UI shell with a Python FastAPI backend and SvelteKit frontend. Plugins contribute Web Components that render in named UI regions. We're adding a React shell as an alternative frontend that loads the same plugin artifacts, proving the Web Components boundary delivers real portability.

The existing SvelteKit shell stays untouched. Shared TypeScript logic (types, registry client, plugin loader) is extracted into a framework-agnostic `packages/core` package. The React shell consumes that package.

**Trust boundary (v1):** Plugin bundles are trusted local assets served from the Continuum backend (`/plugins/{id}/assets/`). No remote registries, no third-party script URLs. Future work (out of scope): allowlist/signature/checksum verification if remote registries are ever introduced.

**Shadow DOM styling contract:** Plugin Web Components use open shadow DOM (`{ mode: "open" }`). The shell does not reach into shadow roots. Plugins must style themselves using inherited CSS custom variables (`var(--continuum-*)`) and shadow-DOM-safe patterns. Class-based styling from the host will not cross the shadow boundary.

## Repo Structure (Target)

```
continuum/
  src/continuum/              (Python backend — UNCHANGED)
  plugins/                    (Plugin packages — UNCHANGED)
  packages/
    core/                     (NEW — @continuum/core: shared TS types, loader, client)
  web/                        (SvelteKit shell — UNCHANGED during this work)
  web-react/                  (NEW — React shell)
  package.json                (NEW — root npm workspaces + dev scripts)
```

---

## Milestone 0: Workspace Scaffolding

**Goal:** npm workspaces so packages can cross-reference via `@continuum/core`, plus root-level dev scripts for the blessed workflow.

**Create:**
- `package.json` (root):
  ```json
  {
    "private": true,
    "workspaces": ["packages/*", "web", "web-react"],
    "scripts": {
      "dev:core": "npm -w @continuum/core run dev",
      "dev:web": "npm -w continuum-web run dev",
      "dev:web-react": "npm -w @continuum/web-react run dev",
      "dev:all": "concurrently \"npm run dev:core\" \"npm run dev:web-react\"",
      "dev:full": "concurrently \"npm run dev:core\" \"npm run dev:web-react\" \"cd src/continuum && continuum dev\"",
      "build:core": "npm -w @continuum/core run build",
      "build:web-react": "npm run build:core && npm -w @continuum/web-react run build",
      "test:core": "npm -w @continuum/core test",
      "test:e2e": "npm -w @continuum/web-react run test:e2e"
    },
    "devDependencies": {
      "concurrently": "^9.0.0"
    }
  }
  ```

  `dev:full` runs the complete stack: core watch + React dev server + Python backend. `dev:all` omits the backend for when it's already running separately.

**Modify:**
- `src/continuum/main.py` — add `"http://localhost:5174"` to the CORS `allow_origins` list, guarded by environment:
  ```python
  import os
  _dev_origins = [
      "http://localhost:5173",  # SvelteKit Vite dev server
      "http://localhost:5174",  # React Vite dev server
  ]
  _prod_origins = os.environ.get("CONTINUUM_CORS_ORIGINS", "").split(",") if os.environ.get("CONTINUUM_CORS_ORIGINS") else []
  allow_origins = _prod_origins if _prod_origins else [
      *_dev_origins,
      "http://localhost:4040",
      "capacitor://localhost",
  ]
  ```
  This ensures dev origins are only active when no explicit production CORS config is provided.

**Verify:** `npm install` at root succeeds. `cd web && npm run dev` still works.

---

## Milestone 1: `packages/core` — Contract-Driven Shared Package

**Goal:** Create `@continuum/core` with types, runtime validation, registry client, plugin loader, command client, region resolver, and event contracts. Zero framework dependencies.

**Key principle:** The backend `/api/registry` response is the source of truth. Types are defined to match that contract. `fetchRegistry()` validates the response at runtime with zod so both shells fail consistently on schema drift.

### Files to create

```
packages/core/
  package.json          — name: @continuum/core, vite lib mode, vitest, zod dep
  tsconfig.json         — strict, ES2022, declaration output
  vite.config.ts        — library build → dist/index.js + dist/index.d.ts
  src/
    index.ts            — barrel export
    types.ts            — all shared types (see below)
    schemas.ts          — zod schemas mirroring types; used for runtime validation
    registry-client.ts  — fetchRegistry(), fetchHealth(), fetchDiagnostics()
    plugin-loader.ts    — loadBundle(), preloadBundles(), waitForElement() (no Svelte stores)
    command-client.ts   — executeCommand(), getAuditLog()
    region-resolver.ts  — resolveRegions(snapshot, perspective) → RenderPlan
    regions.ts          — REGION_DEFS data constant (slot IDs, cardinality, descriptions)
    events.ts           — ContinuumEventMap, event detail types
    __tests__/
      region-resolver.test.ts
      plugin-loader.test.ts
      schemas.test.ts
```

### Types (in `types.ts`)

Defined to match the backend API contract (`/api/registry` response shape):

| Type | Notes |
|------|-------|
| `Perspective` | `{ id, label, route_prefix, description }` |
| `NavTarget` | `{ type: 'panel'\|'drawer'\|'command'\|'route', panel_id?, drawer_id?, command_id?, route? }` |
| `UiContribution` | All contribution fields including `props?: Record<string, unknown>` (see Props section below) |
| `PluginDescriptor` | `{ id, name, version, status, discovery_index, required, error, contribution_count }` |
| `RegistrySnapshot` | `{ lifecycle_state, registry_fingerprint, perspectives, regions, commands, plugins, diagnostics }` |
| `RegionId` | String literal union of the 8 slot IDs (derived from `REGION_DEFS`) |
| `LifecycleState` | `'booting'\|'discovering_plugins'\|'loading_plugins'\|'resolving_registry'\|'ready'\|'degraded'\|'stopping'\|'stopped'` |
| `DangerLevel` | `'safe'\|'confirm'\|'danger'` |
| `BundleLoadState` | `'pending'\|'loading'\|'defining'\|'ready'\|'failed'` |
| `BundleError` | `{ phase: BundleLoadState, message: string, bundleUrl: string, elementTag?: string }` |
| `CommandExecuteRequest` | `{ command_id, args?, dry_run?, confirmed? }` |
| `CommandExecuteResult` | `{ command_id, status, audit_id, duration_ms, result, error, dry_run_preview, requires_confirmation, danger_level }` |
| `AuditEntry` | `{ audit_id, command_id, user_id, timestamp, status, duration_ms, args_redacted, error, context }` |
| `BrandConfig` | `{ appName, logoUrl?, accentColor?, themeVars? }` |
| `HostServices` | `{ navigate?, getAuthToken?, telemetry? }` |
| `ContinuumShellConfig` | `{ registryUrl?, brand?, hostServices?, defineTimeout? }` |
| `RenderPlan` | `{ regions: Record<string, UiContribution[]>, activePerspective }` |

### UiContribution.props — formalized

`UiContribution` includes `props?: Record<string, unknown>` as an explicit optional field. This is the host-to-plugin data channel:

- The backend registry already includes `props` on `PanelContribution` and `DrawerContribution` (defined in `src/continuum/domain/contributions.py`)
- `WebComponentHost` sets these imperatively on the custom element via `ref[key] = value`
- Props are JSON-serializable (they come from the registry snapshot)
- This is the only supported mechanism for passing initial data to plugins; plugins that need ongoing data use `continuum:*` CustomEvents

### Zod schemas (in `schemas.ts`)

Runtime validation at the `fetchRegistry()` boundary. Core enums are locked down with `z.enum()`; contributions use `passthrough()` for forward compat:

```ts
import { z } from 'zod';

export const LifecycleStateSchema = z.enum([
  'booting', 'discovering_plugins', 'loading_plugins',
  'resolving_registry', 'ready', 'degraded', 'stopping', 'stopped',
]);

export const DangerLevelSchema = z.enum(['safe', 'confirm', 'danger']);

export const NavTargetTypeSchema = z.enum(['panel', 'drawer', 'command', 'route']);

export const NavTargetSchema = z.object({
  type: NavTargetTypeSchema,
  panel_id: z.string().optional(),
  drawer_id: z.string().optional(),
  command_id: z.string().optional(),
  route: z.string().optional(),
});

export const PerspectiveSchema = z.object({
  id: z.string(),
  label: z.string(),
  route_prefix: z.string(),
  description: z.string(),
});

export const UiContributionSchema = z.object({
  type: z.string(),
  plugin_id: z.string(),
  discovery_index: z.number(),
  priority: z.number().optional(),
  slot: z.string().optional(),
  perspective: z.string().optional(),
  component: z.string().optional(),
  bundle_url: z.string().nullable().optional(),
  label: z.string().optional(),
  icon: z.string().optional(),
  target: NavTargetSchema.optional(),
  id: z.string().optional(),
  props: z.record(z.unknown()).optional(),
  danger_level: DangerLevelSchema.optional(),
  // ... remaining optional fields
}).passthrough(); // allow unknown fields for forward compat

export const PluginDescriptorSchema = z.object({
  id: z.string(),
  name: z.string(),
  version: z.string(),
  status: z.string(),
  discovery_index: z.number(),
  required: z.boolean(),
  error: z.string().nullable(),
  contribution_count: z.number(),
});

export const RegistrySnapshotSchema = z.object({
  lifecycle_state: LifecycleStateSchema,
  registry_fingerprint: z.string(),
  perspectives: z.array(PerspectiveSchema),
  regions: z.record(z.string(), z.array(UiContributionSchema)),
  commands: z.array(UiContributionSchema),
  plugins: z.array(PluginDescriptorSchema),
  diagnostics: z.object({
    conflicts: z.array(z.unknown()),
    missing_required: z.array(z.string()),
    warnings: z.array(z.string()),
  }),
});
```

`fetchRegistry()` calls `RegistrySnapshotSchema.parse(data)`. The `passthrough()` on contributions allows the backend to add fields without breaking clients. Core enums (`LifecycleState`, `DangerLevel`, `NavTarget.type`) are locked down with `z.enum()` so schema drift is caught immediately.

Future: optionally generate these from FastAPI's OpenAPI spec.

### Region definitions (in `regions.ts`)

Centralized, data-driven region/slot definitions so adding regions doesn't require widespread changes:

```ts
export const REGION_DEFS = {
  'ui.slot.left_nav':    { cardinality: 'many', description: 'Perspective switcher + action triggers' },
  'ui.slot.header':      { cardinality: 'one',  description: 'Title, search, user profile' },
  'ui.slot.main':        { cardinality: 'many', description: 'Primary content, perspective-scoped' },
  'ui.slot.right_rail':  { cardinality: 'many', description: 'Secondary panels' },
  'ui.slot.footer':      { cardinality: 'one',  description: 'Status bar' },
  'ui.slot.modal':       { cardinality: 'many', description: 'Overlay dialogs' },
  'ui.slot.drawer':      { cardinality: 'many', description: 'Slide-in panels' },
  'ui.slot.toast_stack': { cardinality: 'many', description: 'Transient notifications' },
} as const;

export type RegionId = keyof typeof REGION_DEFS;
```

Both shells import `REGION_DEFS` instead of hardcoding slot IDs.

### Plugin loader

Replace Svelte stores (`writable`, `derived`) with vanilla JS:
- Plain `Map<string, BundleState>` for bundle states
- `Set<string>` for loaded URLs (dedup)
- Callback registration: `onBundleStateChange(url, cb)` for framework-specific subscribers
- Public API: `loadBundle(url)`, `preloadBundles(urls)`, `isElementDefined(tag)`, `waitForElement(tag, timeout?)`
- `getBundleState(url)`, `getBundleError(url)` — read from plain Map

**Bundle identity and dedup rules:**
- Primary dedup key is `bundle_url` (string). Same URL is never loaded twice regardless of which contribution references it.
- Multiple contributions can share the same `bundle_url` (e.g., `continuum.sample_signal` has 3 components in one bundle). The bundle is loaded once; each component is instantiated separately via `customElements.whenDefined(tag)`.
- Same `plugin_id` with different `bundle_url` (theoretically possible if a plugin ships multiple bundles): each URL is loaded independently, deduped by URL.
- Bundle state tracking uses a `BundleKey` that pairs `bundle_url` (primary) with `plugin_id` (for reporting). Inspector and error cards display both.

**Error payload (`BundleError`):**
```ts
interface BundleError {
  phase: 'loading' | 'defining' | 'timeout';  // where the failure occurred
  message: string;                              // human-readable error
  bundleUrl: string;                            // the script URL that failed
  elementTag?: string;                          // which custom element tag (if in defining phase)
  pluginId?: string;                            // owning plugin (for error cards)
}
```

This structured error is returned by `getBundleError(url)` and consumed by `WebComponentHost` error cards and the Inspector.

### Registry client

```ts
export async function fetchRegistry(
  baseUrl: string = '',
  options?: { signal?: AbortSignal }
): Promise<RegistrySnapshot> {
  const response = await fetch(`${baseUrl}/api/registry`, { signal: options?.signal });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  const data = await response.json();
  return RegistrySnapshotSchema.parse(data);
}
```

Accepts an `AbortSignal` so callers (React hooks, embed unmount) can cancel in-flight requests.

### Region resolver

```ts
function resolveRegions(snapshot: RegistrySnapshot, activePerspective: string): RenderPlan
```
Filters contributions by perspective scope, returns region -> ordered contributions map.

**Verify:**
- `npm run build:core` produces `dist/index.js` + `dist/index.d.ts`
- `npm run test:core` passes (region-resolver, plugin-loader, schema validation tests)
- Schema tests: valid registry JSON passes; missing `registry_fingerprint` throws ZodError; invalid `lifecycle_state` value (not in enum) throws ZodError

---

## Milestone 2: `web-react` — React Shell with Plugin Rendering

**Goal:** Functional React shell that loads registry, renders shell layout, and hosts plugin Web Components. This is the core deliverable.

### Files to create

```
web-react/
  package.json          — @continuum/web-react, react 19, @continuum/core workspace dep
  tsconfig.json         — standard Vite+React config
  vite.config.ts        — port 5174, proxy /api + /plugins to :4040
  index.html            — Vite entry
  src/
    main.tsx            — ReactDOM.createRoot, renders <App />
    App.tsx             — fetches registry, renders <Shell /> or loading/error
    app.css             — duplicate of web/src/app.css design tokens

    hooks/
      useRegistry.ts      — wraps fetchRegistry() in useState/useEffect, uses AbortController
      usePerspective.ts   — active perspective state + resolveRegions() via useMemo
      useBundleLoader.ts  — wraps loadBundle() + waitForElement() in React state

    components/
      Shell.tsx + Shell.css
      Header.tsx + Header.css
      LeftNav.tsx + LeftNav.css
      NavItem.tsx + NavItem.css
      WebComponentHost.tsx        — THE critical React↔WC bridge
      WebComponentErrorBoundary.tsx — React error boundary for WC slots
      ComponentLoader.tsx + ComponentLoader.css
      RegionSlot.tsx + RegionSlot.css
      Footer.tsx + Footer.css
      LoadingScreen.tsx
      ErrorScreen.tsx
```

### Shell layout (mirrors `web/src/lib/components/Shell.svelte`)

```
┌─────────────────────────────────────────┐
│ Header (logo, perspective label, ⌘K, status) │
├────┬──────────────────────┬─────────────┤
│Nav │ Main                 │ Right Rail  │
│    │ (RegionSlot main)    │ (RegionSlot)│
│    │                      │             │
├────┴──────────────────────┴─────────────┤
│ Footer (plugin count, fingerprint)       │
└─────────────────────────────────────────┘
```

### Layout parity checklist

The React shell must match the SvelteKit shell on these points:

- [ ] **Regions rendered:** `left_nav`, `header` (ONE), `main` (MANY, perspective-filtered), `right_rail` (MANY, perspective-filtered), `footer` (ONE). `modal`, `drawer`, `toast_stack` rendered as overlays when triggered.
- [ ] **Perspective switching:** Clicking a nav item with `target.type === 'panel'` sets the active perspective. Main and right rail contributions filter to match.
- [ ] **Nav grouping:** "Views" group (perspective nav items) at top, "Actions" group (commands, drawers) at bottom, separated by a spacer.
- [ ] **Status info:** Footer shows plugin count and registry fingerprint. Header shows lifecycle state badge (green "READY" when ready).
- [ ] **Keyboard shortcuts:** Cmd/Ctrl+K opens command palette, Escape dismisses overlays.
- [ ] **Right rail conditional:** Right rail only renders when there are contributions for the active perspective.

### WebComponentHost — Hardened Rules

This is where React + Web Components gets tricky. The implementation must follow these rules precisely:

**Definition gating (must-have):**
- Do NOT render the custom element tag until `customElements.whenDefined(tag)` resolves
- `useBundleLoader` hook manages the lifecycle: `pending` → `loading` (bundle script loading) → `defining` (waiting for `whenDefined`) → `ready` (safe to render) → or `failed`
- Timeout on `whenDefined` — default 5s, configurable via `ContinuumShellConfig.defineTimeout` so devs can raise it when debugging slow bundles
- On timeout or error, render a consistent error card (not a blank slot), structured with `BundleError` payload
- The error state is surfaced in the Inspector (M4)

**Property vs attribute policy:**
- **Primitives** (string, number, boolean): set as attributes via JSX — React 19 handles this correctly for custom elements
- **Complex values** (objects, arrays, functions): set imperatively via `ref.current[propName] = value` in a `useEffect` — never pass through JSX (React would stringify them)
- `contribution.props` (from the registry snapshot) is always set imperatively since it's `Record<string, unknown>`
- Document this rule in a code comment at the top of `WebComponentHost.tsx`

**Event listener lifecycle:**
- Attach `continuum:navigate`, `continuum:command`, `continuum:telemetry` listeners only AFTER the element exists in DOM (in `useEffect`, gated on ref)
- Always detach on unmount AND on contribution change (cleanup function)
- Event handler is stable (via `useCallback`) to avoid unnecessary re-subscribes

**Error boundary:**
- Wrap each `WebComponentHost` instance in `WebComponentErrorBoundary`
- On any error (bundle load, define timeout, runtime error), render a consistent error card showing: plugin_id, component tag, bundle_url, error phase, error message
- The slot continues to function (other contributions in the same region are unaffected)

**Implementation approach:**
```tsx
function WebComponentHost({ contribution, onEvent }: Props) {
  const { state, error } = useBundleLoader(contribution.bundle_url, contribution.component);
  const containerRef = useRef<HTMLDivElement>(null);
  const elementRef = useRef<HTMLElement | null>(null);

  // Create and mount element imperatively once defined
  useEffect(() => {
    if (state !== 'ready' || !contribution.component || !containerRef.current) return;
    const el = document.createElement(contribution.component);
    containerRef.current.appendChild(el);
    elementRef.current = el;
    return () => { el.remove(); elementRef.current = null; };
  }, [state, contribution.component]);

  // Set complex props imperatively (never via JSX)
  useEffect(() => {
    if (!elementRef.current || !contribution.props) return;
    for (const [key, value] of Object.entries(contribution.props)) {
      (elementRef.current as any)[key] = value;
    }
  }, [contribution.props]);

  // Wire events — attach only after element exists, always cleanup
  const stableOnEvent = useCallback(
    (e: Event) => onEvent?.(e as CustomEvent),
    [onEvent]
  );
  useEffect(() => {
    const el = elementRef.current;
    if (!el) return;
    el.addEventListener('continuum:navigate', stableOnEvent);
    el.addEventListener('continuum:command', stableOnEvent);
    el.addEventListener('continuum:telemetry', stableOnEvent);
    return () => {
      el.removeEventListener('continuum:navigate', stableOnEvent);
      el.removeEventListener('continuum:command', stableOnEvent);
      el.removeEventListener('continuum:telemetry', stableOnEvent);
    };
  }, [stableOnEvent]);

  if (state === 'failed') return <ErrorCard contribution={contribution} error={error} />;
  if (state !== 'ready') return <LoadingSpinner tag={contribution.component} />;
  return <div ref={containerRef} data-plugin={contribution.plugin_id} />;
}
```

### CSS strategy

Each component gets a co-located `.css` file. All styles use `--continuum-*` tokens (identical to Svelte shell). `app.css` is a copy of `web/src/app.css` design tokens.

**Verify:**
- Start the full stack: `npm run dev:full` (or start backend separately + `npm run dev:all`)
- `http://localhost:5174` shows shell layout
- Signal perspective shows sample_signal plugin panels (metrics, timeline, alerts) as Web Components
- Clicking nav items switches perspectives and main/right-rail content filters
- Right rail disappears when perspective has no right-rail contributions
- Footer shows plugin count and fingerprint
- Header shows lifecycle state badge
- SvelteKit shell at `:5173` still works
- Same plugin JS bundles render identically in both shells

---

## Milestone 3: Command Palette, Drawer, and Events

**Goal:** Full interaction parity with the SvelteKit shell.

### Files to create

```
web-react/src/
  hooks/
    useCommandExecution.ts   — wraps executeCommand() from @continuum/core
    useKeyboardShortcuts.ts  — Cmd+K → palette, Escape → dismiss
    useContinuumEvents.ts    — captures plugin CustomEvents, stores recent N

  components/
    CommandPalette.tsx + CommandPalette.css  — search, keyboard nav, execute, confirm
    ConfirmDialog.tsx + ConfirmDialog.css    — danger/confirm command dialog
    Drawer.tsx + Drawer.css                 — slide-in panel with ComponentLoader
```

### Modify
- `Shell.tsx` — add command palette toggle, drawer state, event wiring, keyboard shortcuts

**Verify:**
- Cmd+K opens command palette, typing filters, Enter executes
- Confirm/danger commands show confirmation dialog
- Drawer opens with chat Web Component when nav action triggers it
- Escape dismisses overlays

---

## Milestone 4: Inspector, Branding, Embed API, and Smoke Test

**Goal:** Systems inspector for dev confidence, branding support, embeddable `ContinuumConsole` with clean lifecycle, and one E2E smoke test that proves the thesis.

### Files to create

```
web-react/src/
  hooks/
    useBranding.ts           — applies BrandConfig as CSS vars on :root

  components/
    Inspector.tsx + Inspector.css  — tabbed view (see below)

  contexts/
    ShellContext.tsx          — React context: registry, renderPlan, perspective, events

  ContinuumConsole.tsx       — public embed component
  index.ts                   — public exports: ContinuumConsole, types

web-react/
  e2e/
    smoke.spec.ts            — Playwright smoke test
  playwright.config.ts
```

### Inspector tabs

| Tab | Data source | Shows |
|-----|-------------|-------|
| Plugins | `registry.plugins` | id, version, status, contribution count |
| Contributions | `registry.regions` (all) | plugin_id, component tag, slot, perspective, priority |
| Render Plan | `resolveRegions()` output | current perspective's resolved region → contributions |
| Events | `useContinuumEvents()` | recent CustomEvents from plugins (type, detail, timestamp) |
| Diagnostics | `registry.diagnostics` | conflicts, warnings, missing required |

### Embed API — `ContinuumConsole`

```tsx
import { ContinuumConsole } from '@continuum/web-react';

<ContinuumConsole config={{
  registryUrl: '/api/registry',
  brand: { appName: 'MyApp', accentColor: '#ff6600' },
  hostServices: { navigate: (path) => router.push(path) }
}} />
```

**Mounting contract (must-haves for clean embed lifecycle):**
- **Abort in-flight fetches on unmount:** `useRegistry` creates an `AbortController`; the cleanup function calls `controller.abort()`. No orphaned network requests.
- **Remove dynamically created WC elements on unmount:** Each `WebComponentHost` cleanup removes its `document.createElement`'d element from the DOM and nulls the ref.
- **Detach all event listeners on unmount:** All `continuum:*` event listeners are detached in `useEffect` cleanup functions. No leaked document-level listeners.
- **Reset CSS variable overrides on unmount:** `useBranding` cleanup restores any `--continuum-*` overrides it set on `document.documentElement`.
- **No global side effects:** `ContinuumConsole` does not modify global state (no `window.*` assignments, no module-level singletons that persist across mounts). The plugin loader's `Set<string>` dedup cache is the one exception (intentional — prevents re-downloading bundles on remount).

### Playwright smoke test

One test that proves the core thesis: React shell loads real plugins as Web Components. Uses Playwright's `webServer` config to start services automatically — no manual backend/shell startup required.

**`playwright.config.ts`:**
```ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  webServer: [
    {
      command: 'cd ../.. && continuum dev',
      port: 4040,
      reuseExistingServer: true,
      timeout: 30000,
    },
    {
      command: 'npm run dev',
      port: 5174,
      reuseExistingServer: true,
      timeout: 15000,
    },
  ],
});
```

**`e2e/smoke.spec.ts`:**
```ts
import { test, expect } from '@playwright/test';

test('React shell loads plugin Web Components', async ({ page }) => {
  await page.goto('http://localhost:5174');

  // Shell rendered
  await expect(page.locator('.shell')).toBeVisible();

  // Registry loaded — footer shows plugin count
  await expect(page.locator('.footer')).toContainText('Plugins:');

  // Custom element class is registered in the browser
  const isDefined = await page.evaluate(
    () => customElements.get('continuum-sample-signal-metrics') !== undefined
  );
  expect(isDefined).toBe(true);

  // At least one plugin container is rendered with the correct data-plugin attribute
  const pluginContainer = page.locator('[data-plugin="continuum.sample_signal"]');
  await expect(pluginContainer.first()).toBeVisible({ timeout: 10000 });

  // The actual custom element exists inside the container
  const elementExists = await pluginContainer.first().evaluate(
    el => el.querySelector('continuum-sample-signal-metrics') !== null
  );
  expect(elementExists).toBe(true);
});
```

### Modify
- `App.tsx` — use `ContinuumConsole` internally (proves embed API works in standalone mode)

**Verify:**
- Systems perspective shows inspector with accurate data
- Changing BrandConfig.accentColor propagates to shell + plugin Web Components
- `npm run test:e2e` passes (Playwright starts backend + dev server automatically)
- ContinuumConsole mounts/unmounts cleanly (no leaked listeners, no orphaned elements, no dangling fetches)

---

## Key Source Files (reference during implementation)

| File | What to extract/mirror |
|------|----------------------|
| `web/src/lib/stores/registry.ts` | TypeScript types + fetch logic → `packages/core/src/types.ts`, `registry-client.ts` |
| `web/src/lib/services/pluginLoader.ts` | Loader logic → `packages/core/src/plugin-loader.ts` |
| `web/src/lib/services/commandService.ts` | Command client → `packages/core/src/command-client.ts` |
| `web/src/lib/components/Shell.svelte` | Layout structure → `web-react/src/components/Shell.tsx` |
| `web/src/lib/components/ComponentLoader.svelte` | WC mounting pattern → `web-react/src/components/WebComponentHost.tsx` |
| `web/src/lib/components/RegionSlot.svelte` | Region rendering → `web-react/src/components/RegionSlot.tsx` |
| `web/src/lib/components/NavItem.svelte` | Nav icons/layout → `web-react/src/components/NavItem.tsx` |
| `web/src/lib/components/CommandPalette.svelte` | Command UI → `web-react/src/components/CommandPalette.tsx` |
| `web/src/lib/components/Drawer.svelte` | Drawer panel → `web-react/src/components/Drawer.tsx` |
| `web/src/app.css` | Design tokens → `web-react/src/app.css` |
| `src/continuum/main.py` | CORS config (environment-aware) |

## Dev Workflow (blessed)

| Command | What it does |
|---------|-------------|
| `npm run dev:full` | Runs everything: core watch + React dev server + Python backend |
| `npm run dev:all` | Core watch + React dev server (backend started separately) |
| `npm run dev:core` | Vite watch-build on `packages/core` |
| `npm run dev:web` | SvelteKit dev server on :5173 |
| `npm run dev:web-react` | React dev server on :5174 |
| `npm run build:core` | One-shot build of `packages/core` |
| `npm run build:web-react` | Builds core first, then React shell |
| `npm run test:core` | Vitest unit tests for core |
| `npm run test:e2e` | Playwright smoke test (auto-starts backend + dev server) |

Both shells are independently runnable. `@continuum/core` is the only shared dependency. In CI: `build:core` → `build:web-react` ordering is enforced by the script chaining.

## Risks

1. **React 19 custom element support** — Mitigated by the hardened WebComponentHost rules: definition gating via `whenDefined()`, imperative element creation, prop/event attachment via refs. The primary approach (imperative `document.createElement` + `appendChild`) avoids React's JSX custom element handling entirely.

2. **CSS token parity** — Both shells must provide identical `--continuum-*` variables. Duplicating `app.css` is intentional for now. Plugins use shadow DOM with `{ mode: "open" }` — CSS variables inherit through shadow boundaries, but class-based styling does not. Plugins must style themselves via CSS vars and shadow-DOM-safe patterns.

3. **Build order** — `packages/core` must build before `web-react`. Enforced by `build:web-react` script chaining and `dev:all`/`dev:full` running core in watch mode.

4. **Schema drift** — Mitigated by zod validation with locked-down enums (`z.enum()`) in `fetchRegistry()`. Both shells fail identically on schema changes. `passthrough()` on contributions allows additive backend changes.
