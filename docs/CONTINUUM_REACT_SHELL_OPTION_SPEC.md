# Continuum — React Shell Option Spec (Core + Shell Subpackages)

**Status:** Draft (planning input)  
**Scope:** Add a React-based shell option **without** renaming the existing `continuum` package, and **without** turning the repo into a multi-package monorepo.  
**Key decision:** Keep **framework-agnostic core** and **framework-specific shells** as **subpackages under** `continuum/src/continuum/`.

---

## 1. Intent

Continuum is a **portable control-plane console** that can be:

1. **Deployed standalone** (as its own console app), and/or  
2. **Embedded into a parent application** as that app’s control plane surface (brandable, extensible, and able to load that parent app’s plugins).

We want to introduce a **React shell** (as an alternative to the SvelteKit shell) primarily to compare host ergonomics and to ensure plugin UI loading is **boring and consistent** across hosts.

**Non-negotiable constraint:** UI plugins are loaded via a **Web Components boundary** (custom elements), so plugins do not couple to the host UI framework.

---

## 2. Goals

### 2.1 Functional goals
- Add a **React shell option** that renders the same Continuum regions/panels as the SvelteKit shell.
- Maintain **plugin UI portability**: plugins ship as Web Components; the host shell loads plugin scripts and instantiates custom elements.
- Keep Continuum importable/embeddable: a parent app can embed Continuum as a console surface and supply:
  - branding config
  - registry provider (or registry URL)
  - optional host services (navigation, telemetry, storage, auth token provider)

### 2.2 Engineering goals
- Keep the existing project layout **inside a single `continuum` package**, with explicit subpackage boundaries:
  - `continuum/src/continuum/core/**` (framework-agnostic)
  - `continuum/src/continuum/shell/**` (framework-specific adapters)
- Enforce the dependency boundary: **core never imports from shell or UI frameworks**.
- Provide a build-time “selector” so deployments can choose **React** or **SvelteKit** shell.

---

## 3. Non-goals

- Replacing SvelteKit.
- Forcing plugins to be React components.
- Runtime switching between shells within a single production artifact (allowed for local demos, optional).
- Creating a full monorepo publishing strategy now (can be deferred).

---

## 4. Architecture Overview

### 4.1 Core vs Shell responsibilities

**Core (`src/continuum/core`)**
- Registry snapshot types + validation
- Plugin lifecycle model (installed/ready/active, etc.)
- Region/slot resolution (MECE layout composition and ordering rules)
- Switchboard/registry client interfaces
- Event contracts (what plugins emit; what the host can send)

**Shells (`src/continuum/shell/*`)**
- UI layout and routing
- Web Component script loader + dedupe
- DOM instantiation of plugin custom elements
- Event wiring (CustomEvents in/out)
- Branding application (CSS vars / tokens)

**Key boundary rule:** plugins are Web Components. Shells are just hosts that render regions.

---

## 5. Repository Layout (Required)

> This is the updated, explicit layout requirement from the latest design decision.

```
continuum/
  src/
    continuum/
      core/
        registry/
        lifecycle/
        region_resolver/
        switchboard_client/
        types/
        index.ts

      shell/
        react/
          app/
          components/
          wc_loader/
          index.ts

        sveltekit/
          app/
          routes/
          wc_loader/
          index.ts
```

### 5.1 Optional (future-friendly) addition
If you later want “embed-anywhere” as a single tag, add:

```
      console_wc/
        element/
        index.ts
```

…but this is optional for the React-shell milestone.

---

## 6. Public APIs (Contracts)

### 6.1 Core contracts (must be framework-agnostic)

**`RegistrySnapshot` (example shape)**
- plugins: list of plugins with id, version, state, assets
- contributions: contributions to regions (by region id), with ordering metadata
- regions: declared regions and constraints (optional; can also be host-defined)

**Core exports (`src/continuum/core/index.ts`) should include:**
- Types:
  - `RegistrySnapshot`, `PluginDescriptor`, `UiContribution`, `RegionId`, `LifecycleState`
- Functions:
  - `resolveRegions(snapshot, layoutSpec) -> RenderPlan`
  - `validateSnapshot(snapshot) -> { ok, errors }`
- Interfaces:
  - `RegistryProvider` (fetch snapshot)
  - `TelemetrySink` (emit events)
  - `HostServices` (optional: navigation, auth token, storage)

### 6.2 Shell contracts (React)

`src/continuum/shell/react/index.ts` should export one of:
- `ContinuumConsole` React component (embed path), and/or
- `mountContinuumConsole(domNode, config)` (standalone mount helper)

**`ContinuumShellConfig`**
- `registry`: `RegistryProvider` OR `registryUrl`
- `brand`: `BrandConfig` (CSS vars, logo, appName)
- `layout`: `LayoutSpec` (regions and placement)
- `hostServices?`: `HostServices`
- `assetLoader?`: override for loading plugin scripts

### 6.3 Branding contract
- Use CSS variables as the stable seam:
  - `--continuum-bg`, `--continuum-fg`, `--continuum-accent`, etc.
- Brand config may set:
  - `appName`, `logoUrl`, `accentColor`, `themeVars`

---

## 7. Web Components Plugin Boundary (Required)

### 7.1 Plugin artifact requirements
A UI plugin provides:
- A JS module bundle that calls `customElements.define("my-plugin-panel", ...)`
- Optional CSS (inlined or linked)
- Emits `CustomEvent`s for interactions.

### 7.2 Contribution record requirements
Each `UiContribution` includes:
- `regionId` (where it renders)
- `elementTag` (custom element name)
- `scriptUrl` (module to load/define element)
- `order` (number) and/or `before/after` constraints (optional, but pick one strategy)
- `props` (JSON-serializable initial state/context)

### 7.3 Data in, events out
- Host passes props via:
  - attributes for primitives
  - **properties** for objects
- Plugin emits CustomEvents (bubbling/composed):
  - `continuum:navigate`
  - `continuum:command`
  - `continuum:telemetry`

---

## 8. React Shell Implementation Requirements

### 8.1 RegionRenderer
- Input: `RenderPlan` (from core resolver)
- Output: DOM with region containers and plugin panels

### 8.2 Web Component loader + dedupe
- Maintain a global map keyed by `(pluginId, pluginVersion)` or `scriptUrl`
- Load via `<script type="module" src="...">` injection or dynamic `import()`
- Prevent duplicate loads on rerender
- Handle errors (expose in inspector UI)

### 8.3 Web Component host wrapper
- React wrapper component that:
  - renders `<{elementTag} />`
  - sets complex props via `ref.current[propName] = value`
  - wires CustomEvents via `ref.current.addEventListener(...)`

### 8.4 Inspector surface (required for dev confidence)
React shell must include a minimal “Systems” inspector that shows:
- loaded plugins: id, version, lifecycle state
- contributions: regionId, elementTag, scriptUrl, active/errored
- resolved render plan (region -> ordered list of contributions)
- last N events received from plugins (optional but very useful)

---

## 9. Shell Selection & Deployment

### 9.1 Build-time selection (required)
- Environment variable: `CONTINUUM_SHELL=react|sveltekit`
- CI should build/test both (matrix), even if you deploy only one.

### 9.2 Standalone deployment
- React shell builds to a static bundle (or node server) depending on your chosen tooling.
- SvelteKit shell continues as-is.

### 9.3 Optional dual-serve for comparison
For local evaluation, you may serve both shells under:
- `/ui/react/*`
- `/ui/svelte/*`
with `/` controlled by `CONTINUUM_DEFAULT_SHELL`.

This is optional; keep production deploy simple (one shell per deploy).

---

## 10. Portability: Parent App Embedding

### 10.1 Embed scenario
A parent app imports `ContinuumConsole` and passes:
- brand config
- registry provider (or URL)
- optional host services (routing integration, auth token function, telemetry)

### 10.2 Parent app plugins
Parent app can contribute additional Web Component plugins by:
- hosting plugin script assets
- registering them into the registry snapshot (or having the registry service include them)
- Continuum renders them through normal region resolution

**Guarantee:** No changes required to Continuum shells to support parent plugins, as long as contributions follow the Web Components contract.

---

## 11. Boundary Enforcement (Required)

### 11.1 ESLint / tooling rule
Add a rule set that forbids:
- `src/continuum/core/**` importing:
  - `react`, `react-dom`, `svelte`, `@sveltejs/*`, etc.
  - anything under `src/continuum/shell/**`

### 11.2 TypeScript path aliases (recommended)
- `@continuum/core` -> `src/continuum/core/index.ts`
- `@continuum/shell-react` -> `src/continuum/shell/react/index.ts`
- `@continuum/shell-sveltekit` -> `src/continuum/shell/sveltekit/index.ts`

---

## 12. Acceptance Criteria

### 12.1 Functional acceptance
- React shell can load a registry snapshot and render at least 3 regions.
- React shell loads plugin scripts once, instantiates custom elements, and displays their UI.
- CustomEvents from plugins are received by the host and reflected in the inspector.
- Branding config changes are reflected without code changes.

### 12.2 Regression acceptance
- Existing SvelteKit shell still works and can load the same plugins.
- The same plugin artifact (same `scriptUrl` bundle and `elementTag`) renders in both shells.

### 12.3 Portability acceptance
- A minimal parent “host app” can embed `ContinuumConsole` (React) and supply:
  - registry provider
  - brand config
  - host navigation handler
- Parent can add one additional plugin contribution and it renders without modifying Continuum code.

---

## 13. Implementation Plan Outline (for the dev agent to expand)

1. Create folder structure under `src/continuum/core` and `src/continuum/shell/react`.
2. Move/confirm core framework-agnostic logic lives in `core/` (types, resolver, registry client).
3. Add React shell app scaffold (routing optional; start minimal).
4. Implement plugin script loader + dedupe.
5. Implement `WebComponentHost` wrapper for setting properties + wiring events.
6. Implement `RegionRenderer` driven by `RenderPlan` from core.
7. Add “Systems Inspector” view.
8. Add boundary enforcement (lint + tsconfig paths).
9. Add build-time selector wiring and CI matrix builds.
10. Add minimal embed example (optional but recommended for portability proof).

---

## 14. Open Decisions (should be made early in the plan)

- Plugin version strategy for custom element tag naming:
  - single active version per element tag (recommended), vs versioned tag names
- Script loading mechanism:
  - dynamic `import()` vs module `<script>` injection (pick based on hosting/CORS)
- Registry snapshot source:
  - local JSON during dev vs live registry service endpoint
