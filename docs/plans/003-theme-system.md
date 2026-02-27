# Plan: Theme System (Core Seam)

**Date:** 2026-02-27
**Status:** Draft (v3.0)
**Reference:** `CONTINUUM_V1_ARCH_SPEC.md`, `002-dynamic-plugin-ui-loading.md`

---

## Overview

Add a **theming system** to Continuum's core framework. The core owns everything: built-in themes, the theme engine, a `[[contributions.theme]]` contribution type for plugins, FOUC prevention, and a compact theme selector in the shell footer.

No theme plugin ships with Continuum. Consuming apps (e.g., Squad Ops) provide their own theme plugins to add branded palettes and optionally override the selector UI.

### Design Principles

1. **CSS Custom Properties are the contract** — Continuum already defines all visual tokens as `--continuum-*` CSS custom properties in `app.css`. Themes are alternate sets of these token values. No structural HTML or component changes needed.
2. **Core owns the mechanism and ships defaults** — The shell knows how to apply a theme (set tokens, persist selection, prevent FOUC) and ships with 3 built-in themes so theming works out of the box.
3. **`[[contributions.theme]]` is a first-class contribution type** — Just like `nav`, `panel`, `drawer`, and `command`, themes are registered via the plugin manifest and `ctx.register_contribution("theme", ...)`. Any consuming app's plugin can ship additional themes.
4. **Zero functionality impact** — Themes only change CSS custom property values. Layout, navigation, plugin rendering, commands, and all other behavior remain untouched.
5. **Graceful degradation** — Even with no plugins installed, the 3 built-in themes are always available. The footer selector always works.

---

## End State Definition

> Clone Continuum → `continuum dev` → footer shows theme selector → pick Light → entire UI recolors instantly.
> Refresh → theme persists. OS switches to light mode → theme auto-follows.
> A consuming app installs a theme plugin with `[[contributions.theme]]` → those themes appear in the footer selector automatically alongside the built-ins.

---

## Architecture

### What the Core Provides

```
┌─────────────────────────────────────────────────────────────────┐
│                        CORE FRAMEWORK                           │
│                                                                 │
│  1. Theme contribution type (domain model + manifest schema)    │
│  2. Theme registry (built-in + plugin themes, served via API)   │
│  3. Theme engine (shell-side: apply tokens, persist, restore)   │
│  4. FOUC prevention (inline script in app.html)                 │
│  5. Built-in themes (Default Dark, Light, High Contrast)        │
│  6. Shell theme selector (compact control in footer bar)        │
│  7. prefers-color-scheme detection (auto light/dark on boot)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### What a Consuming App's Plugin Can Do

```
┌─────────────────────────────────────────────────────────────────┐
│               CONSUMING APP THEME PLUGIN (optional)             │
│                                                                 │
│  1. Additional themes via [[contributions.theme]]               │
│  2. Override built-in themes by contributing matching IDs        │
│  3. Enhanced selector UI (drawer, popover, etc.) via            │
│     [[contributions.drawer]] or [[contributions.panel]]         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Built-in Themes

The core ships three built-in themes so that theming works immediately after `git clone` + `continuum dev`, with no plugins required:

| Theme | ID | Category | Why Built-in |
|-------|----|----------|--------------|
| **Default Dark** | (implicit) | dark | The baseline — existing `app.css` `:root` tokens. Always present, fallback when theme is removed. |
| **Light** | `light` | light | Required for `prefers-color-scheme` support — the core needs a light theme to auto-switch when OS is in light mode. |
| **High Contrast** | `high-contrast` | dark | Accessibility is a core platform concern, not an optional plugin feature. |

Built-in themes are defined in the backend (`src/continuum/domain/themes.py`) and are always present in the registry response, regardless of installed plugins. They are not `[[contributions.theme]]` entries — they're hard-coded as always-available themes. Plugin-contributed themes merge alongside them.

If a plugin contributes a theme with the same ID as a built-in (e.g., `id = "light"`), the plugin version overrides the built-in. This lets consuming apps customize the core themes.

### How Theming Works (End-to-End)

```
                     Boot Sequence
                     ═════════════
  1. Server builds registry: built-in themes + plugin [[contributions.theme]]
  2. /api/registry response includes "themes" array (built-in + contributed)
  3. Shell loads, inline <script> reads localStorage('continuum-theme')
  4. If saved theme ID found → sets data-theme attribute immediately (FOUC prevention)
  5. If no saved theme → check prefers-color-scheme, auto-select light if OS prefers light
  6. Shell fetches /api/registry → receives theme definitions with full token maps
  7. Theme engine applies matching theme's tokens via <style> injection
  8. Dashboard renders fully themed — no flash
  9. Footer shows compact theme selector with all available themes

                     Theme Switch (Footer Selector)
                     ══════════════════════════════
  1. User clicks theme selector in footer bar
  2. Picks from dropdown of available themes
  3. Shell theme engine applies instantly (data-theme + <style> injection)
  4. Persists theme ID to localStorage
  5. Next page load → step 3-5 of boot sequence restores it

                     Theme Switch (Plugin UI — optional)
                     ═══════════════════════════════════
  1. Consuming app's plugin opens a drawer/panel with a richer theme picker
  2. User clicks a theme → plugin dispatches continuum:theme-apply event
  3. Shell listens, delegates to theme engine → applies instantly
  4. Same persistence behavior as footer selector
```

---

## Detailed Design

### 1A. Domain Model: `ThemeContribution`

**File:** `src/continuum/domain/contributions.py`

Add a `ThemeContribution` dataclass alongside the existing contribution types:

```python
@dataclass(frozen=True)
class ThemeContribution:
    """A theme contribution providing a complete set of CSS custom property overrides."""

    id: str
    name: str
    description: str
    category: str  # "dark" or "light"
    preview_colors: list[str]  # 5 representative hex colors for swatch display
    tokens: dict[str, str]  # {"--continuum-bg-primary": "#ffffff", ...}
    plugin_id: str = ""  # Empty for built-in themes
    builtin: bool = False
```

### 1B. Manifest Schema: `[[contributions.theme]]`

**File:** `src/continuum/domain/manifest.py`

Add `ThemeContributionManifest` for validating theme entries in `plugin.toml`:

```python
@dataclass
class ThemeContributionManifest:
    """Theme contribution manifest entry."""

    id: str
    name: str
    description: str = ""
    category: str = "dark"  # "dark" or "light"
    preview_colors: list[str] = field(default_factory=list)

@dataclass
class ContributionsManifest:
    """All contributions declared in a plugin manifest."""

    nav: list[NavContributionManifest] = field(default_factory=list)
    panel: list[PanelContributionManifest] = field(default_factory=list)
    drawer: list[DrawerContributionManifest] = field(default_factory=list)
    command: list[CommandContributionManifest] = field(default_factory=list)
    diagnostic: list[DiagnosticContributionManifest] = field(default_factory=list)
    theme: list[ThemeContributionManifest] = field(default_factory=list)  # NEW
```

**Manifest example** (what a consuming app's plugin would write):

```toml
[[contributions.theme]]
id = "squadops-dark"
name = "Squad Ops Dark"
description = "Official Squad Ops branded dark theme"
category = "dark"
preview_colors = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#533483"]
```

Token maps are registered in the plugin's `__init__.py` via `ctx.register_contribution("theme", {...})` because TOML isn't ideal for 20+ key-value token maps.

### 1C. Built-in Theme Definitions

**File:** `src/continuum/domain/themes.py` (NEW)

The core ships with three built-in themes defined as static data:

```python
"""
Built-in theme definitions.

These themes ship with the core framework and are always available.
Plugins can contribute additional themes via [[contributions.theme]],
or override a built-in by contributing a theme with the same ID.
"""

BUILTIN_THEMES: list[dict] = [
    {
        "id": "light",
        "name": "Light",
        "description": "Clean light theme with white backgrounds",
        "category": "light",
        "builtin": True,
        "preview_colors": ["#ffffff", "#f6f8fa", "#0969da", "#1f2328", "#1a7f37"],
        "tokens": {
            "--continuum-bg-primary": "#ffffff",
            "--continuum-bg-secondary": "#f6f8fa",
            "--continuum-bg-tertiary": "#eaeef2",
            "--continuum-bg-hover": "#d0d7de",
            "--continuum-bg-active": "#0969da1a",
            "--continuum-border": "#d0d7de",
            "--continuum-border-muted": "#eaeef2",
            "--continuum-text-primary": "#1f2328",
            "--continuum-text-secondary": "#656d76",
            "--continuum-text-muted": "#8b949e",
            "--continuum-text-link": "#0969da",
            "--continuum-accent-primary": "#0969da",
            "--continuum-accent-success": "#1a7f37",
            "--continuum-accent-warning": "#9a6700",
            "--continuum-accent-danger": "#d1242f",
            "--continuum-shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.08)",
            "--continuum-shadow-md": "0 4px 12px rgba(0, 0, 0, 0.1)",
            "--continuum-shadow-lg": "0 8px 24px rgba(0, 0, 0, 0.12)",
        },
    },
    {
        "id": "high-contrast",
        "name": "High Contrast",
        "description": "Maximum contrast for accessibility",
        "category": "dark",
        "builtin": True,
        "preview_colors": ["#000000", "#0a0a0a", "#409eff", "#ffffff", "#34d058"],
        "tokens": {
            "--continuum-bg-primary": "#000000",
            "--continuum-bg-secondary": "#0a0a0a",
            "--continuum-bg-tertiary": "#1a1a1a",
            "--continuum-bg-hover": "#2a2a2a",
            "--continuum-bg-active": "#409eff33",
            "--continuum-border": "#505050",
            "--continuum-border-muted": "#333333",
            "--continuum-text-primary": "#ffffff",
            "--continuum-text-secondary": "#f0f0f0",
            "--continuum-text-muted": "#b0b0b0",
            "--continuum-text-link": "#409eff",
            "--continuum-accent-primary": "#409eff",
            "--continuum-accent-success": "#34d058",
            "--continuum-accent-warning": "#ffdf5d",
            "--continuum-accent-danger": "#ff4444",
            "--continuum-shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.5)",
            "--continuum-shadow-md": "0 4px 12px rgba(0, 0, 0, 0.6)",
            "--continuum-shadow-lg": "0 8px 24px rgba(0, 0, 0, 0.7)",
        },
    },
]
```

**Note:** "Default Dark" is NOT in this list — it's the existing `app.css` `:root` tokens. It's always implicitly available as the "no theme selected" state. The footer selector includes it as the first option labeled "Default Dark" that calls `applyTheme(null)`.

### 1D. Registry Resolution for Themes

**File:** `src/continuum/app/registry.py`

Update `build_registry()` to collect theme contributions into a separate list (themes don't go into slots — they're a distinct contribution category, like commands). Built-in themes are prepended before plugin-contributed themes:

```python
from continuum.domain.themes import BUILTIN_THEMES

def build_registry(contributions: list[dict[str, Any]]) -> ResolvedRegistry:
    # ... existing logic ...

    themes: list[dict[str, Any]] = []

    for contrib in contributions:
        contrib_type = contrib.get("type")

        if contrib_type == "command":
            commands.append(contrib)
        elif contrib_type == "theme":
            themes.append(contrib)
        elif contrib_type in ("nav", "panel", "drawer", "diagnostic"):
            # ... existing slot logic ...

    # ... existing slot processing ...

    # Process themes: built-in themes first, then plugin-contributed (sorted by priority)
    plugin_themes = _sort_contributions(themes)

    # Plugin themes can override built-in themes by matching ID
    builtin_ids_overridden = {t["id"] for t in plugin_themes}
    remaining_builtins = [t for t in BUILTIN_THEMES if t["id"] not in builtin_ids_overridden]
    registry.themes = remaining_builtins + plugin_themes

    # ... rest of existing logic ...
```

**File:** `src/continuum/app/registry.py` — Update `ResolvedRegistry`:

```python
@dataclass
class ResolvedRegistry:
    """The resolved contribution registry."""

    slots: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    commands: list[dict[str, Any]] = field(default_factory=list)
    themes: list[dict[str, Any]] = field(default_factory=list)  # NEW
    fingerprint: str = ""
    report: RegistryBuildReport = field(default_factory=RegistryBuildReport)
```

### 1E. API Response: Themes in Registry

**File:** `src/continuum/adapters/web/api.py`

Add `themes` to the `RegistryResponse`:

```python
class RegistryResponse(BaseModel):
    lifecycle_state: str
    registry_fingerprint: str
    perspectives: list[PerspectiveResponse]
    regions: dict[str, list[ContributionResponse]]
    commands: list[ContributionResponse]
    themes: list[ThemeResponse]  # NEW
    plugins: list[PluginResponse]
    diagnostics: DiagnosticsResponse

class ThemeResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    preview_colors: list[str]
    tokens: dict[str, str]
    plugin_id: str = ""
    builtin: bool = False
```

### 1F. Shell Theme Engine

**File:** `web/src/lib/services/themeEngine.ts` (NEW)

The theme engine is the shell-side component that applies theme tokens to the document. It's a small module (~50 lines):

```typescript
const STORAGE_KEY = 'continuum-theme';
const STYLE_ID = 'continuum-theme-overrides';

export interface ThemeDefinition {
  id: string;
  name: string;
  description: string;
  category: 'dark' | 'light';
  preview_colors: string[];
  tokens: Record<string, string>;
  plugin_id?: string;
  builtin?: boolean;
}

/**
 * Apply a theme by injecting its token overrides into the document.
 * Pass null to revert to the default dark theme (clear overrides).
 */
export function applyTheme(theme: ThemeDefinition | null): void {
  const root = document.documentElement;

  // Remove existing theme overrides
  const existing = document.getElementById(STYLE_ID);
  if (existing) existing.remove();

  if (theme) {
    // Inject <style> with token overrides
    const style = document.createElement('style');
    style.id = STYLE_ID;
    const rules = Object.entries(theme.tokens)
      .map(([key, value]) => `  ${key}: ${value};`)
      .join('\n');
    style.textContent = `:root {\n${rules}\n}`;
    document.head.appendChild(style);

    root.setAttribute('data-theme', theme.id);
    localStorage.setItem(STORAGE_KEY, theme.id);
  } else {
    // Revert to default: remove overrides, clear storage
    root.removeAttribute('data-theme');
    localStorage.removeItem(STORAGE_KEY);
  }
}

/** Get the stored theme ID from localStorage. */
export function getStoredThemeId(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

/**
 * Restore the saved theme after registry loads.
 * If the saved ID doesn't match any available theme, clean up.
 * If no theme is saved, check OS preference and auto-select light if appropriate.
 */
export function restoreTheme(themes: ThemeDefinition[]): void {
  const savedId = getStoredThemeId();

  if (savedId) {
    const theme = themes.find(t => t.id === savedId);
    if (theme) {
      applyTheme(theme);
    } else {
      // Stale ID — theme was removed (plugin uninstalled)
      applyTheme(null);
    }
  } else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
    // No saved preference, OS prefers light — auto-select
    const lightTheme = themes.find(t => t.category === 'light');
    if (lightTheme) {
      applyTheme(lightTheme);
    }
  }
}
```

### 1G. Shell Integration (Registry Store + Shell.svelte)

**File:** `web/src/lib/stores/registry.ts`

Add `themes` to the `Registry` interface and create derived stores:

```typescript
export interface Registry {
  // ... existing fields ...
  themes: ThemeDefinition[];  // NEW
}

// NEW: Theme stores
export const themes: Readable<ThemeDefinition[]> = derived(
  registry,
  $registry => $registry?.themes ?? []
);

export const activeThemeId = writable<string | null>(getStoredThemeId());
```

**File:** `web/src/lib/components/Shell.svelte`

Add theme restoration after registry loads, and listen for plugin theme events:

```svelte
<script lang="ts">
  import { restoreTheme, applyTheme } from '$lib/services/themeEngine';
  import { themes, activeThemeId } from '$stores/registry';
  import ThemeSelector from './ThemeSelector.svelte';

  // After registry loads, restore saved theme
  $: if ($themes.length > 0) {
    restoreTheme($themes);
  }

  // Listen for plugin theme-apply events
  onMount(() => {
    function handleThemeApply(e: CustomEvent) {
      const themeId = e.detail?.themeId;
      if (themeId === null) {
        applyTheme(null);
        activeThemeId.set(null);
      } else {
        const theme = $themes.find(t => t.id === themeId);
        if (theme) {
          applyTheme(theme);
          activeThemeId.set(theme.id);
        }
      }
    }
    window.addEventListener('continuum:theme-apply', handleThemeApply);
    return () => window.removeEventListener('continuum:theme-apply', handleThemeApply);
  });
</script>

<!-- Footer -->
<footer class="footer">
  <div class="footer-left">
    <span>Plugins: {$registry?.plugins.length ?? 0}</span>
    <span>Fingerprint: {$registry?.registry_fingerprint ?? ''}</span>
  </div>
  <div class="footer-right">
    <ThemeSelector themes={$themes} />
    <span class="system-status" ...>...</span>
  </div>
</footer>
```

### 1H. Shell Theme Selector (Footer Control)

**File:** `web/src/lib/components/ThemeSelector.svelte` (NEW)

A compact theme selector built into the shell's footer bar. This is the core's built-in UI for switching themes — it works with zero plugins installed.

**Design:** A small clickable control in the footer (next to "System Status") that shows the current theme name and opens a dropdown with all available themes:

```
┌─ Footer ─────────────────────────────────────────────────────────────┐
│ Plugins: 3  Fingerprint: a1b2c3d4    Theme: Default Dark ▾  ● Ready │
│                                       ┌───────────────────┐         │
│                                       │ ● Default Dark  ✓ │         │
│                                       │ ○ Light           │         │
│                                       │ ● High Contrast   │         │
│                                       │ ─────────────────-│         │
│                                       │ ● Squad Ops Dark  │  ← from│
│                                       │ ● Squad Ops HC    │  plugin │
│                                       └───────────────────┘         │
└──────────────────────────────────────────────────────────────────────┘
  ● = dark category   ○ = light category   ✓ = active
```

**Behavior:**
- Always visible in footer (the footer is a core shell region, always rendered)
- Shows current theme name ("Default Dark" when no theme applied)
- Click opens a dropdown listing all themes from the registry (built-in + plugin-contributed)
- Built-in themes listed first, then a separator, then plugin-contributed themes (if any)
- Small dot indicates dark/light category
- Checkmark on active theme
- Click a theme → applies instantly via `applyTheme()`
- Click "Default Dark" → calls `applyTheme(null)` to revert to `:root` baseline
- Dropdown closes on selection or click-outside

**Why the footer?** The footer bar already shows system metadata (plugin count, fingerprint, status). A theme selector is the same kind of operator utility — small, always accessible, not a primary workflow action. Consuming apps can supplement or replace this with a richer UI via their own plugin drawer.

### 1I. FOUC Prevention

**File:** `web/src/app.html`

Add an inline `<script>` in `<head>` that runs before any rendering:

```html
<script>
  // FOUC prevention: apply saved theme immediately before first paint
  (function() {
    var id = localStorage.getItem('continuum-theme');
    if (id) document.documentElement.setAttribute('data-theme', id);
  })();
</script>
```

This sets the `data-theme` attribute immediately. The actual token injection happens later when the registry loads and `restoreTheme()` runs, but the `data-theme` attribute can also be used by CSS selectors for instant visual differentiation if needed.

---

## Built-in Themes

### 1. Default Dark (implicit — `app.css` `:root`)
The existing `app.css` `:root` tokens. Always available. What you get when no theme is selected or when all theme plugins are removed. Not a `ThemeContribution` — it's the baseline.

### 2. Light (`light`)
- White/light gray backgrounds (`#ffffff`, `#f6f8fa`)
- Dark text (`#1f2328`, `#656d76`)
- Blue accents (GitHub light style)
- Lighter shadows (lower opacity)
- Category: light
- **Why built-in:** Required for `prefers-color-scheme: light` OS preference support

### 3. High Contrast (`high-contrast`)
- Pure black background (`#000000`, `#0a0a0a`)
- Pure white text (`#ffffff`, `#f0f0f0`)
- Bright, saturated accent colors
- Enhanced borders (`#505050`) for visibility
- Category: dark
- **Why built-in:** Accessibility is a core platform concern

---

## Plugin Extensibility

Continuum does **not** ship a theme plugin. Consuming apps provide their own. Here's what a consuming app's theme plugin looks like:

### Example: `squadops.themes` plugin

**`plugins/squadops.themes/plugin.toml`:**

```toml
[plugin]
id = "squadops.themes"
name = "Squad Ops Themes"
version = "1.0.0"
description = "Branded themes for Squad Ops dashboard"
required = false

[[contributions.theme]]
id = "squadops-dark"
name = "Squad Ops Dark"
description = "Official branded dark theme"
category = "dark"
preview_colors = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#533483"]

[[contributions.theme]]
id = "squadops-light"
name = "Squad Ops Light"
description = "Official branded light theme"
category = "light"
preview_colors = ["#fafafa", "#f0f0f5", "#0f3460", "#1a1a2e", "#2ecc71"]
```

**`plugins/squadops.themes/__init__.py`:**

```python
SQUADOPS_DARK_TOKENS = {
    "--continuum-bg-primary": "#1a1a2e",
    "--continuum-bg-secondary": "#16213e",
    # ... full token map ...
}

SQUADOPS_LIGHT_TOKENS = {
    "--continuum-bg-primary": "#fafafa",
    "--continuum-bg-secondary": "#f0f0f5",
    # ... full token map ...
}

def register(ctx):
    ctx.register_contribution("theme", {"id": "squadops-dark", "tokens": SQUADOPS_DARK_TOKENS})
    ctx.register_contribution("theme", {"id": "squadops-light", "tokens": SQUADOPS_LIGHT_TOKENS})
```

These themes would appear in the footer selector automatically alongside the built-in themes. If Squad Ops wants a richer picker UI, they add a `[[contributions.drawer]]` to the same plugin.

---

## Implementation Phases

### Phase 1: Core Theme Seam (Backend)

**Goal:** Theme contributions flow through the backend pipeline. Built-in themes are always available.

**Files to create:**
- `src/continuum/domain/themes.py` — Built-in theme definitions (Light, High Contrast)

**Files to modify:**
- `src/continuum/domain/contributions.py` — Add `ThemeContribution` dataclass
- `src/continuum/domain/manifest.py` — Add `ThemeContributionManifest`, update `ContributionsManifest`
- `src/continuum/app/registry.py` — Update `ResolvedRegistry` with `themes` field, update `build_registry()` to collect built-in + plugin theme contributions
- `src/continuum/app/runtime.py` — Add `themes` to `RegistryState`, wire through `_resolve_registry()`, add `get_themes()` accessor
- `src/continuum/adapters/web/api.py` — Add `themes` to `RegistryResponse`, include in registry endpoint

**Verification:**
- `pytest tests/` passes (no regressions)
- `GET /api/registry` response includes a `themes` array with 2 built-in themes (Light, High Contrast) even with zero theme plugins installed
- A plugin with `[[contributions.theme]]` contributes additional themes that appear after built-ins
- Plugin theme with same ID as built-in overrides the built-in version

### Phase 2: Core Theme Seam (Frontend)

**Goal:** Shell can apply, persist, restore themes, and provides a built-in selector in the footer.

**Files to create:**
- `web/src/lib/services/themeEngine.ts` — `applyTheme()`, `getStoredThemeId()`, `restoreTheme()`
- `web/src/lib/components/ThemeSelector.svelte` — Compact footer dropdown for theme selection

**Files to modify:**
- `web/src/lib/stores/registry.ts` — Add `themes` to `Registry` interface, add `themes` derived store, add `activeThemeId` store
- `web/src/lib/components/Shell.svelte` — Call `restoreTheme()` after registry loads (~5 lines), add `continuum:theme-apply` event listener (~10 lines), add `<ThemeSelector>` to footer
- `web/src/app.html` — Add inline FOUC prevention script (5 lines)

**Verification:**
- Footer shows theme selector with "Default Dark", "Light", "High Contrast" (built-in themes)
- Clicking a theme in the footer selector recolors the dashboard instantly
- Refreshing the page restores the theme without visible flash
- `applyTheme(null)` reverts to default dark theme
- All existing plugin panels recolor correctly (they already use `var(--continuum-*)`)
- This works with zero plugins installed — built-in themes are always available
- `prefers-color-scheme: light` auto-selects Light theme when no preference stored

---

## File Summary

### Core Framework (Created)

- `src/continuum/domain/themes.py` — Built-in theme definitions (Light, High Contrast)
- `web/src/lib/services/themeEngine.ts` — Theme application engine
- `web/src/lib/components/ThemeSelector.svelte` — Compact footer theme selector

### Core Framework (Modified)

- `src/continuum/domain/contributions.py` — Add `ThemeContribution` dataclass
- `src/continuum/domain/manifest.py` — Add `ThemeContributionManifest`, update `ContributionsManifest`
- `src/continuum/app/registry.py` — Add `themes` to `ResolvedRegistry`, update `build_registry()` with built-in themes
- `src/continuum/app/runtime.py` — Add `themes` to `RegistryState`, add `get_themes()`
- `src/continuum/adapters/web/api.py` — Add `themes` to `RegistryResponse`
- `web/src/lib/stores/registry.ts` — Add `themes` to `Registry` interface, add derived stores
- `web/src/lib/components/Shell.svelte` — Add `restoreTheme()` call, event listener, `<ThemeSelector>` in footer
- `web/src/app.html` — Add inline FOUC prevention script (5 lines)

### Nothing Created in `plugins/`

No theme plugin ships with Continuum. The `plugins/` directory is unchanged.

---

## Verification Checklist

### Core Seam (Backend)
- [ ] `ThemeContribution` dataclass exists in domain model
- [ ] `ThemeContributionManifest` validates in manifest schema
- [ ] Built-in themes defined in `src/continuum/domain/themes.py`
- [ ] `build_registry()` collects built-in + plugin themes into `ResolvedRegistry.themes`
- [ ] `/api/registry` includes `themes` array with 2 built-in themes (zero plugins)
- [ ] Plugin-contributed themes appear after built-ins in the array
- [ ] Plugin theme with same ID as built-in overrides the built-in
- [ ] Existing tests pass with no regressions

### Core Seam (Frontend)
- [ ] Theme engine `applyTheme()` overrides all `--continuum-*` tokens
- [ ] `applyTheme(null)` cleanly reverts to shell defaults
- [ ] Theme persists in `localStorage` across page refreshes
- [ ] `restoreTheme()` restores saved theme after registry loads
- [ ] FOUC prevention script sets `data-theme` before first paint
- [ ] Stale theme ID (plugin removed) is cleaned up on next load
- [ ] Footer theme selector shows all available themes
- [ ] Footer selector works with zero plugins (built-in themes only)
- [ ] `continuum:theme-apply` custom event works from plugin → shell
- [ ] `prefers-color-scheme: light` auto-selects Light theme when no preference stored

### Plugin Extensibility
- [ ] A consuming app's `[[contributions.theme]]` entries appear in the footer selector
- [ ] Plugin themes merge alongside built-in themes in `/api/registry`
- [ ] Plugin theme overriding a built-in ID replaces the built-in version
- [ ] Removing a theme plugin leaves built-in themes still working
- [ ] Existing plugin panels (Signal, Systems, etc.) recolor correctly
- [ ] No functionality regression — navigation, commands, drawers all work

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token map incomplete | Theme partially applied, visual glitches | Built-in themes define ALL 17 `--continuum-*` tokens; schema validation warns on missing tokens |
| Plugin provides invalid token values | CSS breaks for that theme | Token values are strings — CSS handles invalid values gracefully (falls back to inherited/initial) |
| localStorage stale (theme plugin removed) | Saved theme can't be applied | `restoreTheme()` detects missing theme ID and cleans up — falls back to default |
| FOUC on slow connections | Brief flash of wrong theme | Inline `<script>` sets `data-theme` before first paint; token injection follows after registry loads |
| `prefers-color-scheme` conflicts with saved preference | Unexpected theme on load | Saved preference always wins; OS preference is only used when no saved preference exists |
