# Plan: Theme System (Core Seam + Theme Selector Plugin)

**Date:** 2026-02-27
**Status:** Draft (v2.1)
**Reference:** `CONTINUUM_V1_ARCH_SPEC.md`, `002-dynamic-plugin-ui-loading.md`

---

## Overview

Add a **theming system** to Continuum using a **hybrid architecture**: the core framework owns the theme application mechanism, a new `[[contributions.theme]]` contribution type, and FOUC prevention, while a companion plugin (`continuum.theme_selector`) provides the theme picker UI and a curated theme pack.

This follows Continuum's existing pattern: the host defines the seam (like perspectives and regions), plugins contribute content (like panels and nav items). Themes work the same way — the host defines what a theme *is* and how it's applied; plugins provide the actual themes and the UI to switch between them.

### Design Principles

1. **CSS Custom Properties are the contract** — Continuum already defines all visual tokens as `--continuum-*` CSS custom properties in `app.css`. Themes are alternate sets of these token values. No structural HTML or component changes needed.
2. **Core owns the mechanism, plugins own the content** — The shell knows how to apply a theme (set tokens, persist selection, prevent FOUC). Plugins contribute theme definitions and the selector UI.
3. **`[[contributions.theme]]` is a first-class contribution type** — Just like `nav`, `panel`, `drawer`, and `command`, themes are registered via the plugin manifest and `ctx.register_contribution("theme", ...)`. Any plugin can ship themes.
4. **Zero functionality impact** — Themes only change CSS custom property values. Layout, navigation, plugin rendering, commands, and all other behavior remain untouched.
5. **Graceful degradation** — If no theme plugins are installed, the shell renders with its default dark tokens. The core theme mechanism is inert with no themes registered. No errors, no warnings.

---

## End State Definition

> Install the theme selector plugin → restart → "Appearance" appears in nav → open drawer → pick a theme → entire UI recolors instantly.
> Refresh → theme persists. Uninstall the plugin → dashboard reverts to default dark theme.
> A *different* plugin can also contribute themes via `[[contributions.theme]]` — they appear in the selector automatically.

---

## Architecture

### Responsibility Split

```
┌─────────────────────────────────────────────────────────────────┐
│                        CORE FRAMEWORK                           │
│                                                                 │
│  1. Theme contribution type (domain model + manifest schema)    │
│  2. Theme registry (collect themes from plugins, serve via API) │
│  3. Theme engine (shell-side: apply tokens, persist, restore)   │
│  4. FOUC prevention (inline script in app.html)                 │
│  5. Built-in themes (Default Dark, Light, High Contrast)        │
│  6. Shell theme selector (compact control in footer bar)        │
│  7. prefers-color-scheme detection (set initial light/dark)     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    THEME SELECTOR PLUGIN                        │
│                                                                 │
│  1. Additional themes (midnight, nord, solarized-dark) —        │
│     contributed via [[contributions.theme]]                     │
│  2. Enhanced theme selector drawer (visual picker with swatches │
│     preview cards, category grouping)                           │
│  3. Nav item ("Appearance" button to open drawer)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Built-in vs Plugin-Contributed Themes

The core ships three built-in themes so that theming works immediately after `git clone` + `continuum dev`, with no plugins required:

| Theme | Source | Why Built-in |
|-------|--------|--------------|
| **Default Dark** | `app.css` `:root` tokens | The baseline — always present, fallback when theme is removed |
| **Light** | Built-in theme definition | Required for `prefers-color-scheme` support — the core needs a light theme to switch to when OS is in light mode |
| **High Contrast** | Built-in theme definition | Accessibility is a core platform concern, not an optional plugin feature |

The plugin adds "flavor" themes (Midnight Blue, Nord, Solarized Dark) that are nice-to-have but not essential for core functionality. These are purely aesthetic options that belong in a plugin.

Built-in themes are defined in the backend (always present in the registry response, regardless of installed plugins) and are **not** `[[contributions.theme]]` entries — they're hard-coded in the registry builder as always-available themes. Plugin-contributed themes merge alongside them.

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

                     Theme Switch (Shell Selector)
                     ═════════════════════════════
  1. User clicks theme selector in footer bar
  2. Cycles or picks from dropdown of available themes
  3. Shell theme engine applies instantly (data-theme + <style> injection)
  4. Persists theme ID to localStorage
  5. Next page load → step 3-5 of boot sequence restores it

                     Theme Switch (Plugin Drawer)
                     ════════════════════════════
  1. User opens Appearance drawer → sees theme cards with swatches
  2. Clicks a theme card → plugin dispatches continuum:theme-apply event
  3. Shell listens, delegates to theme engine → applies instantly
  4. Same persistence behavior as shell selector
```

### Token Flow

```
app.css (shell)                     Theme Engine (shell)
┌─────────────────────┐             ┌───────────────────────────┐
│ :root {             │             │ <style id="continuum-     │
│   --continuum-bg-*  │  overrides  │  theme-overrides">        │
│   --continuum-text-*│ ◄────────── │ [data-theme="nord"] {     │
│   ...               │             │   --continuum-bg-*: ...   │
│ }                   │             │ }                         │
└─────────────────────┘             └───────────────────────────┘
        ▲ always present                    ▲ injected at runtime
        │ (fallback)                        │ from registry data
```

1. Shell defines tokens on `:root` (current behavior, unchanged — this is the default dark theme)
2. Theme engine sets `data-theme` attribute on `<html>`
3. Theme engine injects a `<style>` element with `[data-theme="x"] { ... }` token overrides
4. CSS specificity ensures `[data-theme]` overrides win over `:root`
5. When no theme is active, `:root` defaults apply — graceful fallback

### Token Categories Themed

All existing `--continuum-*` visual tokens are themeable:

| Category | Token Pattern | Example |
|----------|---------------|---------|
| Backgrounds | `--continuum-bg-*` | `--continuum-bg-primary`, `--continuum-bg-secondary` |
| Text | `--continuum-text-*` | `--continuum-text-primary`, `--continuum-text-muted` |
| Accents | `--continuum-accent-*` | `--continuum-accent-primary`, `--continuum-accent-danger` |
| Borders | `--continuum-border*` | `--continuum-border`, `--continuum-border-muted` |
| Shadows | `--continuum-shadow-*` | `--continuum-shadow-sm`, `--continuum-shadow-lg` |
| Radii | `--continuum-radius-*` | `--continuum-radius-sm`, `--continuum-radius-md` |

Layout tokens (`--continuum-nav-width`, `--continuum-header-height`) are intentionally **excluded** from theming to preserve structural consistency.

---

## Part 1: Core Framework Changes

### 1A. Theme Contribution Type (Domain Model)

**File:** `src/continuum/domain/contributions.py`

Add `ThemeContribution` alongside the existing contribution dataclasses:

```python
@dataclass(frozen=True)
class ThemeContribution:
    """
    A theme contribution.

    Themes provide alternate sets of CSS custom property values
    that change the visual appearance of the dashboard.
    """

    id: str                    # e.g., "midnight", "nord"
    name: str                  # Display name: "Midnight Blue"
    description: str = ""      # Short description
    category: str = "dark"     # "dark" or "light" — for grouping and prefers-color-scheme
    tokens: dict[str, str] = field(default_factory=dict)  # CSS custom property overrides
    preview_colors: list[str] = field(default_factory=list)  # 4-5 hex colors for swatch display
```

### 1B. Theme Manifest Schema

**File:** `src/continuum/domain/manifest.py`

Add `ThemeContributionManifest` and include it in `ContributionsManifest`:

```python
class ThemeContributionManifest(BaseModel):
    """Theme contribution in manifest."""

    id: str
    name: str
    description: str = ""
    category: str = Field(default="dark", pattern="^(dark|light)$")
    preview_colors: list[str] = Field(default_factory=list)

    # Note: tokens are NOT in the manifest — they are too verbose for TOML.
    # Tokens are registered programmatically via ctx.register_contribution("theme", ...)
    # in __init__.py. The manifest declares the theme metadata only.


class ContributionsManifest(BaseModel):
    """All contributions from a plugin."""

    nav: list[NavContributionManifest] = Field(default_factory=list)
    panel: list[PanelContributionManifest] = Field(default_factory=list)
    drawer: list[DrawerContributionManifest] = Field(default_factory=list)
    command: list[CommandContributionManifest] = Field(default_factory=list)
    diagnostic: list[DiagnosticContributionManifest] = Field(default_factory=list)
    theme: list[ThemeContributionManifest] = Field(default_factory=list)  # NEW
```

**Manifest usage (in plugin.toml):**

```toml
# Theme metadata declared in manifest (lightweight)
[[contributions.theme]]
id = "midnight"
name = "Midnight Blue"
description = "Deep navy with electric blue accents"
category = "dark"
preview_colors = ["#0b1628", "#111d35", "#58a6ff", "#e6edf3", "#3fb950"]

# Full token maps registered in __init__.py (programmatic, not TOML)
```

**Design decision — why split manifest and Python registration:**
Theme token maps contain 20+ key-value pairs. Encoding them in TOML is verbose and error-prone. The manifest declares theme *metadata* (id, name, category, preview colors for the selector UI). The Python `register()` function provides the full token map. This mirrors how commands work: manifest declares metadata, Python provides the handler.

### 1C. Built-in Theme Definitions

**File:** `src/continuum/domain/themes.py` (NEW)

The core ships with three built-in themes defined as static data. These are always available regardless of installed plugins:

```python
"""
Built-in theme definitions.

These themes ship with the core framework and are always available.
Plugins can contribute additional themes via [[contributions.theme]].
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

**Note:** "Default Dark" is NOT in this list — it's the existing `app.css` `:root` tokens. It's always implicitly available as the "no theme selected" state. The shell selector includes it as the first option labeled "Default Dark" that calls `applyTheme(null)`.

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
    registry.themes = list(BUILTIN_THEMES) + plugin_themes

    # ... rest of existing logic ...
```

Built-in themes always appear first in the list (before plugin themes). If a plugin contributes a theme with the same ID as a built-in (e.g., `id = "light"`), the plugin version overrides the built-in — allowing plugins to customize the core themes. Duplicate detection compares by ID.

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

**File:** `src/continuum/app/runtime.py`

Add `themes` to `RegistryState` and wire it through resolution:

```python
@dataclass
class RegistryState:
    """Resolved registry state."""
    # ... existing fields ...
    themes: list[dict[str, Any]] = field(default_factory=list)  # NEW
```

In `_resolve_registry()`:
```python
self._registry.themes = self._resolved_registry.themes
```

Add accessor:
```python
def get_themes(self) -> list[dict[str, Any]]:
    """Get registered themes."""
    return self._registry.themes
```

**File:** `src/continuum/adapters/web/api.py`

Update `RegistryResponse` and the registry endpoint:

```python
class RegistryResponse(BaseModel):
    """Registry payload response."""
    # ... existing fields ...
    themes: list[dict[str, Any]]  # NEW

@router.get("/api/registry", response_model=RegistryResponse)
async def registry(request: Request) -> RegistryResponse:
    runtime = request.app.state.runtime
    regions = runtime.get_regions_with_bundle_urls()

    return RegistryResponse(
        # ... existing fields ...
        themes=runtime.get_themes(),  # NEW
    )
```

### 1F. Shell Theme Engine

**File:** `web/src/lib/services/themeEngine.ts` (NEW)

The shell owns theme application logic — it's not a plugin concern:

```typescript
export interface ThemeDefinition {
  id: string;
  name: string;
  description: string;
  category: 'dark' | 'light';
  tokens: Record<string, string>;
  preview_colors: string[];
  plugin_id: string;
}

const STORAGE_KEY = 'continuum-theme';
const STYLE_ID = 'continuum-theme-overrides';

/**
 * Apply a theme by injecting its token overrides.
 * Pass null to revert to shell defaults.
 */
export function applyTheme(theme: ThemeDefinition | null): void {
  const el = document.documentElement;
  const existing = document.getElementById(STYLE_ID);

  if (!theme) {
    delete el.dataset.theme;
    existing?.remove();
    localStorage.removeItem(STORAGE_KEY);
    return;
  }

  el.dataset.theme = theme.id;

  const css = `[data-theme="${theme.id}"] {\n` +
    Object.entries(theme.tokens)
      .map(([prop, value]) => `  ${prop}: ${value};`)
      .join('\n') +
    '\n}';

  if (existing) {
    existing.textContent = css;
  } else {
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = css;
    document.head.appendChild(style);
  }

  localStorage.setItem(STORAGE_KEY, theme.id);
}

/**
 * Get the stored theme ID from localStorage.
 */
export function getStoredThemeId(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

/**
 * Restore a theme from the registry by stored ID.
 * Called by the shell after registry loads.
 */
export function restoreTheme(themes: ThemeDefinition[]): void {
  const storedId = getStoredThemeId();
  if (!storedId) return;

  const theme = themes.find(t => t.id === storedId);
  if (theme) {
    applyTheme(theme);
  } else {
    // Stored theme no longer available (plugin removed) — clean up
    localStorage.removeItem(STORAGE_KEY);
    document.documentElement.removeAttribute('data-theme');
    document.getElementById(STYLE_ID)?.remove();
  }
}
```

### 1G. Shell Integration (Registry Store + Shell.svelte)

**File:** `web/src/lib/stores/registry.ts`

Add theme-related types, store, and auto-restore:

```typescript
// Add to Registry interface
export interface Registry {
  // ... existing fields ...
  themes: ThemeDefinition[];
}

// Derived store for themes
export const themes: Readable<ThemeDefinition[]> = derived(
  registry,
  $registry => $registry?.themes ?? []
);

// Active theme store
export const activeThemeId = writable<string | null>(getStoredThemeId());
```

**File:** `web/src/lib/components/Shell.svelte`

After `fetchRegistry()` completes, restore the saved theme:

```typescript
import { restoreTheme, applyTheme } from '$lib/services/themeEngine';
import { themes } from '$stores/registry';

// In onMount, after fetchRegistry():
$effect(() => {
  if ($themes.length > 0) {
    restoreTheme($themes);
  }
});

// Listen for theme-apply events from plugin UI
onMount(() => {
  function handleThemeApply(e: CustomEvent) {
    const { themeId } = e.detail;
    if (themeId === null) {
      applyTheme(null);
    } else {
      const theme = $themes.find(t => t.id === themeId);
      if (theme) applyTheme(theme);
    }
  }
  window.addEventListener('continuum:theme-apply', handleThemeApply);
  return () => window.removeEventListener('continuum:theme-apply', handleThemeApply);
});
```

This is a small addition to Shell.svelte — the shell invokes the theme engine after registry data arrives and listens for theme-apply events. No theme UI, no picker, no drawer — that's all plugin territory.

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
│                                       │ ● Midnight Blue   │  ← from│
│                                       │ ● Nord            │  plugin │
│                                       │ ● Solarized Dark  │         │
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
- Click "Default Dark" → calls `applyTheme(null)` to revert
- Dropdown closes on selection or click-outside

**Why the footer?** The footer bar (`Shell.svelte:177-188`) already shows system metadata (plugin count, fingerprint, status). A theme selector is the same kind of operator utility — small, always accessible, not a primary workflow action. It doesn't warrant a nav slot or a dedicated panel.

**Integration in Shell.svelte:**

```svelte
<!-- Footer -->
<footer class="footer">
  <div class="footer-left">
    <span>Plugins: {$registry?.plugins.length ?? 0}</span>
    <span>Fingerprint: {$registry?.registry_fingerprint ?? ''}</span>
  </div>
  <div class="footer-right">
    <ThemeSelector themes={$themes} />   <!-- NEW -->
    <span class="system-status" ...>...</span>
  </div>
</footer>
```

### 1I. FOUC Prevention

**File:** `web/src/app.html`

Add an inline script that runs before any rendering:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%sveltekit.assets%/favicon.png" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Continuum</title>
    <script>
      // FOUC prevention: apply saved theme before any rendering.
      // Sets data-theme attribute immediately; full token injection
      // happens when the shell loads the registry and theme engine.
      (function() {
        var t = localStorage.getItem('continuum-theme');
        if (t) document.documentElement.setAttribute('data-theme', t);
      })();
    </script>
    %sveltekit.head%
  </head>
  <body data-sveltekit-preload-data="hover">
    <div style="display: contents">%sveltekit.body%</div>
  </body>
</html>
```

**How this handles the gap:** The inline script sets `data-theme` synchronously (before CSS paints). The actual token overrides arrive shortly after when the theme engine processes the registry response. During this brief window, `[data-theme="x"]` is set but the override `<style>` isn't injected yet — so `:root` tokens still apply. This means a very brief flash is theoretically possible but in practice the registry fetch + theme engine runs within the first paint cycle on localhost and within ~100ms on production.

---

## Part 2: Theme Selector Plugin

### Plugin Structure

```
plugins/
  continuum.theme_selector/
    plugin.toml                    # Manifest (themes + drawer + nav)
    __init__.py                    # Python: register themes with full token maps
    ui/
      src/
        ThemeSelector.svelte       # Drawer panel: theme picker UI
        index.js                   # Bundle entry point
      vite.config.js
      package.json
    dist/
      plugin.js                    # Built Web Component bundle
```

### Manifest (`plugin.toml`)

```toml
[plugin]
id = "continuum.theme_selector"
name = "Theme Selector"
version = "1.0.0"
description = "Additional themes and enhanced theme picker for Continuum"
required = false

[plugin.ui]
tag_prefix = "continuum-theme-selector"
bundle = "plugin.js"

# Additional theme definitions (metadata only — tokens in __init__.py)
# Note: Light and High Contrast are built into the core.
# This plugin adds "flavor" themes.
[[contributions.theme]]
id = "midnight"
name = "Midnight Blue"
description = "Deep navy with electric blue accents"
category = "dark"
preview_colors = ["#0b1628", "#111d35", "#58a6ff", "#e6edf3", "#3fb950"]

[[contributions.theme]]
id = "nord"
name = "Nord"
description = "Arctic, bluish-gray color palette"
category = "dark"
preview_colors = ["#2e3440", "#3b4252", "#88c0d0", "#eceff4", "#a3be8c"]

[[contributions.theme]]
id = "solarized-dark"
name = "Solarized Dark"
description = "Ethan Schoonover's precision color scheme"
category = "dark"
preview_colors = ["#002b36", "#073642", "#268bd2", "#839496", "#b58900"]

# Drawer contribution: enhanced theme picker with swatch previews
[[contributions.drawer]]
id = "theme_selector"
component = "continuum-theme-selector-picker"
title = "Appearance"
width = "360px"

# Nav contribution: button to open enhanced theme picker drawer
[[contributions.nav]]
slot = "ui.slot.left_nav"
label = "Appearance"
icon = "palette"
priority = 10

[contributions.nav.target]
type = "drawer"
drawer_id = "theme_selector"
```

### Python Entrypoint (`__init__.py`)

The Python side registers theme contributions with full token maps. This plugin provides three "flavor" themes (Light and High Contrast are built into the core):

```python
"""
Continuum Theme Selector Plugin.

Provides additional themes and an enhanced visual theme picker drawer.
Theme metadata is declared in plugin.toml; full token maps are
registered here because TOML is not ideal for 20+ key-value token maps.

Note: Light and High Contrast themes are built into the core framework.
This plugin adds flavor themes: Midnight Blue, Nord, Solarized Dark.
"""

MIDNIGHT_TOKENS = {
    "--continuum-bg-primary": "#0b1628",
    "--continuum-bg-secondary": "#111d35",
    "--continuum-bg-tertiary": "#1a2744",
    "--continuum-bg-hover": "#243352",
    "--continuum-bg-active": "#58a6ff33",
    "--continuum-border": "#243352",
    "--continuum-border-muted": "#1a2744",
    "--continuum-text-primary": "#e6edf3",
    "--continuum-text-secondary": "#8b949e",
    "--continuum-text-muted": "#6e7681",
    "--continuum-text-link": "#58a6ff",
    "--continuum-accent-primary": "#58a6ff",
    "--continuum-accent-success": "#3fb950",
    "--continuum-accent-warning": "#d29922",
    "--continuum-accent-danger": "#f85149",
    "--continuum-shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.4)",
    "--continuum-shadow-md": "0 4px 12px rgba(0, 0, 0, 0.5)",
    "--continuum-shadow-lg": "0 8px 24px rgba(0, 0, 0, 0.6)",
}

NORD_TOKENS = {
    "--continuum-bg-primary": "#2e3440",
    "--continuum-bg-secondary": "#3b4252",
    "--continuum-bg-tertiary": "#434c5e",
    "--continuum-bg-hover": "#4c566a",
    "--continuum-bg-active": "#88c0d033",
    "--continuum-border": "#4c566a",
    "--continuum-border-muted": "#434c5e",
    "--continuum-text-primary": "#eceff4",
    "--continuum-text-secondary": "#d8dee9",
    "--continuum-text-muted": "#7b88a1",
    "--continuum-text-link": "#88c0d0",
    "--continuum-accent-primary": "#88c0d0",
    "--continuum-accent-success": "#a3be8c",
    "--continuum-accent-warning": "#ebcb8b",
    "--continuum-accent-danger": "#bf616a",
    "--continuum-shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.3)",
    "--continuum-shadow-md": "0 4px 12px rgba(0, 0, 0, 0.4)",
    "--continuum-shadow-lg": "0 8px 24px rgba(0, 0, 0, 0.5)",
}

SOLARIZED_DARK_TOKENS = {
    "--continuum-bg-primary": "#002b36",
    "--continuum-bg-secondary": "#073642",
    "--continuum-bg-tertiary": "#0a4050",
    "--continuum-bg-hover": "#124d5e",
    "--continuum-bg-active": "#268bd233",
    "--continuum-border": "#124d5e",
    "--continuum-border-muted": "#0a4050",
    "--continuum-text-primary": "#fdf6e3",
    "--continuum-text-secondary": "#93a1a1",
    "--continuum-text-muted": "#657b83",
    "--continuum-text-link": "#268bd2",
    "--continuum-accent-primary": "#268bd2",
    "--continuum-accent-success": "#859900",
    "--continuum-accent-warning": "#b58900",
    "--continuum-accent-danger": "#dc322f",
    "--continuum-shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.3)",
    "--continuum-shadow-md": "0 4px 12px rgba(0, 0, 0, 0.4)",
    "--continuum-shadow-lg": "0 8px 24px rgba(0, 0, 0, 0.5)",
}

THEMES = {
    "midnight": MIDNIGHT_TOKENS,
    "nord": NORD_TOKENS,
    "solarized-dark": SOLARIZED_DARK_TOKENS,
}


def register(ctx):
    """Register plugin contributions."""
    # Register each theme with its full token map
    for theme_id, tokens in THEMES.items():
        ctx.register_contribution("theme", {
            "id": theme_id,
            "tokens": tokens,
        })

    # Drawer: enhanced theme picker with swatch previews
    ctx.register_contribution("drawer", {
        "id": "theme_selector",
        "component": "continuum-theme-selector-picker",
        "title": "Appearance",
        "width": "360px",
    })

    # Nav: button to open enhanced theme picker
    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Appearance",
        "icon": "palette",
        "priority": 10,
        "target": {"type": "drawer", "drawer_id": "theme_selector"},
    })
```

### Theme Selector UI (`ThemeSelector.svelte`)

The drawer provides a richer theme selection experience than the shell's built-in footer selector. It shows all themes (built-in + plugin-contributed) as visual cards with color swatch previews:

```
┌─ Appearance ────────────────────────┐
│                                      │
│  Choose a theme for your dashboard   │
│                                      │
│  Built-in                            │
│  ┌──────────┐  ┌──────────┐         │
│  │ ████████ │  │ ░░░░░░░░ │         │
│  │ Default  │  │ Light    │         │
│  │ Dark   ✓ │  │          │         │
│  └──────────┘  └──────────┘         │
│                                      │
│  ┌──────────┐                        │
│  │ ████████ │                        │
│  │ High     │                        │
│  │ Contrast │                        │
│  └──────────┘                        │
│                                      │
│  Theme Pack                          │
│  ┌──────────┐  ┌──────────┐         │
│  │ ████████ │  │ ████████ │         │
│  │ Midnight │  │ Nord     │         │
│  │ Blue     │  │          │         │
│  └──────────┘  └──────────┘         │
│                                      │
│  ┌──────────┐                        │
│  │ ████████ │                        │
│  │ Solarized│                        │
│  │ Dark     │                        │
│  └──────────┘                        │
│                                      │
│  [Reset to Default]                  │
│                                      │
└──────────────────────────────────────┘
```

Each theme card shows:
- **Color swatch** — `preview_colors` rendered as small color blocks
- **Name** and **category badge** (dark/light)
- **Checkmark** on the active theme
- Click to apply instantly

Themes are grouped: "Built-in" (Default Dark, Light, High Contrast) and "Theme Pack" (plugin-contributed). The grouping uses the `builtin` flag on theme entries from the registry.

**Plugin → Shell communication:** The plugin dispatches a `CustomEvent`:

```javascript
// Plugin dispatches:
this.dispatchEvent(new CustomEvent('continuum:theme-apply', {
  bubbles: true,
  composed: true,
  detail: { themeId: 'nord' }  // or null for default
}));
```

The shell listens for this event (set up in Shell.svelte per section 1G) and delegates to the theme engine. This follows the existing `continuum:*` custom event contract from the V1 arch spec.

---

## All Shipped Themes

### Built-in (Core Framework) — 3 themes

#### 1. Default Dark (implicit — `app.css` `:root`)
The existing `app.css` `:root` tokens. Always available. What you get when no theme is selected or when all theme plugins are removed. Not a `ThemeContribution` — it's the baseline.

#### 2. Light (`light`)
- White/light gray backgrounds (`#ffffff`, `#f6f8fa`)
- Dark text (`#1f2328`, `#656d76`)
- Blue accents (GitHub light style)
- Lighter shadows (lower opacity)
- Category: light
- **Why built-in:** Required for `prefers-color-scheme: light` OS preference support

#### 3. High Contrast (`high-contrast`)
- Pure black background (`#000000`, `#0a0a0a`)
- Pure white text (`#ffffff`, `#f0f0f0`)
- Bright, saturated accent colors
- Enhanced borders (`#505050`) for visibility
- Category: dark
- **Why built-in:** Accessibility is a core platform concern

### Plugin-Contributed (Theme Selector Plugin) — 3 themes

#### 4. Midnight Blue (`midnight`)
- Deep navy backgrounds (`#0b1628`, `#111d35`)
- Blue-tinted text hierarchy
- Electric blue accents
- Category: dark

#### 5. Nord (`nord`)
- Arctic, bluish-gray backgrounds from Nord palette (`#2e3440`, `#3b4252`)
- Cool-toned text (`#eceff4`, `#d8dee9`)
- Frost blue accents (`#88c0d0`, `#81a1c1`)
- Category: dark

#### 6. Solarized Dark (`solarized-dark`)
- Classic Solarized dark backgrounds (`#002b36`, `#073642`)
- Solarized text hierarchy (`#839496`, `#93a1a1`)
- Solarized accent colors (yellow `#b58900`, blue `#268bd2`)
- Category: dark

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
- `GET /api/registry` response includes a `themes` array with 2 built-in themes (Light, High Contrast) even with zero plugins installed
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

### Phase 3: Theme Selector Plugin

**Goal:** Plugin adds 3 flavor themes and an enhanced drawer picker.

**Files to create:**
- `plugins/continuum.theme_selector/plugin.toml`
- `plugins/continuum.theme_selector/__init__.py`
- `plugins/continuum.theme_selector/ui/package.json`
- `plugins/continuum.theme_selector/ui/vite.config.js`
- `plugins/continuum.theme_selector/ui/src/index.js`
- `plugins/continuum.theme_selector/ui/src/ThemeSelector.svelte`

**Verification:**
- `continuum inspect` shows the plugin as loaded with theme + drawer + nav contributions
- Footer selector now shows 6 themes (3 built-in + 3 plugin-contributed)
- Opening "Appearance" drawer shows all 6 themes with visual swatch cards
- Drawer groups themes: "Built-in" and "Theme Pack" sections
- Clicking a theme card in the drawer applies it instantly
- "Reset to Default" reverts to shell defaults
- Theme persists across page refresh
- Build: `cd plugins/continuum.theme_selector/ui && npm install && npm run build` succeeds
- `./scripts/build-plugins.sh` includes theme selector

### Phase 4: Testing & Polish

**Goal:** Confidence that themes don't break anything and the contribution type is solid.

**Tests to add:**
- `tests/test_theme_contributions.py` — Theme contribution type:
  - Theme appears in registry when plugin contributes it
  - Theme tokens are included in API response
  - Multiple plugins can contribute themes (no conflicts — themes are additive)
  - Theme with missing tokens still loads (partial override is valid)
  - Registry fingerprint changes when themes change
- `tests/test_theme_plugin.py` — Plugin integration:
  - Plugin discovery, manifest validation, asset serving
  - Theme selector drawer renders
- Theme engine unit tests (apply, remove, persist, restore, cleanup of stale theme ID)

**Polish:**
- Smooth CSS transitions when switching themes (`transition: background-color var(--continuum-transition-normal), color var(--continuum-transition-normal)`)
- Keyboard navigation within theme grid (arrow keys + enter)
- `prefers-color-scheme` media query: if no theme is stored and a `light` category theme is available, auto-select it when OS is in light mode

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Plugin Web Components use Shadow DOM and don't inherit tokens | V1 uses Shadow DOM OFF (`shadow: 'none'`). Tokens propagate via CSS inheritance. If shadow DOM is enabled later, CSS custom properties still cross shadow boundaries. |
| Flash of default theme on page load | Inline `<script>` in `app.html` sets `data-theme` before any rendering. Theme engine applies full tokens once registry loads. Gap is <100ms and invisible in practice. |
| Theme CSS specificity conflicts | `[data-theme="x"]` selector has higher specificity than `:root`, so overrides win naturally. No `!important` needed. |
| Removing theme plugin leaves stale `data-theme` attribute | Shell's `restoreTheme()` checks if stored ID exists in registry. If not found (plugin removed), it clears the attribute and localStorage. Clean fallback. |
| Third-party plugin uses hardcoded colors instead of tokens | Plugin authoring issue. Document in plugin-quickstart.md that plugins MUST use `var(--continuum-*)` tokens for theme compatibility. |
| Token maps are large — API response bloat | Theme tokens are ~20 key-value pairs each. 5 themes = ~100 extra entries. Negligible compared to existing registry payload. Could optimize later with a separate `/api/themes` endpoint if needed. |
| Plugin-contributed theme has incomplete token coverage | Valid — partial overrides are fine. Missing tokens fall through to `:root` defaults. Document that themes should cover all visual tokens for a consistent look. |
| Multiple plugins contribute themes with the same ID | First by priority + discovery_index wins (same as ONE-slot conflict resolution). Log a warning. Theme IDs should be namespaced by convention. |

---

## Why Hybrid Over Pure Plugin

This plan chose the hybrid approach over the original pure-plugin design for these specific reasons:

1. **FOUC solved cleanly** — The inline `<script>` in `app.html` and `restoreTheme()` in Shell.svelte are core shell code. A plugin can't add an inline script to `app.html` or hook into the shell's boot sequence. With the hybrid, theme restoration is a proper lifecycle step.

2. **No headless component hack** — The v1.0 plan required a `ThemeProvider` contributed as a hidden panel in `ui.slot.footer` just to run initialization code. That abused the contribution model. Now the shell simply calls `restoreTheme()` after loading the registry.

3. **Any plugin can contribute themes** — With `[[contributions.theme]]` as a first-class type, a corporate branding plugin could ship `acme.branding` with `[[contributions.theme]] id = "acme-corporate"` and it would appear in the selector automatically. No coupling to the theme selector plugin.

4. **Token contract is explicit** — The core defines `ThemeContribution` with a `tokens` field. This is the contract. The shell knows exactly what a theme provides and validates it.

5. **`prefers-color-scheme` is a shell concern** — OS light/dark detection should happen before any plugin loads. The shell can check `window.matchMedia('(prefers-color-scheme: light)')` and auto-select an appropriate theme from the registry.

---

## Future Extensions (Not in This Plan)

- **Custom themes** — Let operators define their own token overrides via a theme editor UI
- **Theme API** — Backend endpoint to store themes per-user (instead of localStorage)
- **Per-perspective themes** — Different theme per perspective
- **Scheduling** — Auto-switch between light/dark based on time of day
- **Theme validation** — Warn if a contributed theme doesn't cover all recommended tokens
- **Remote theme packs** — Fetch theme definitions from a URL

---

## Files Modified/Created Summary

### Core Framework (Modified)

- `src/continuum/domain/contributions.py` — Add `ThemeContribution` dataclass
- `src/continuum/domain/manifest.py` — Add `ThemeContributionManifest`, update `ContributionsManifest`
- `src/continuum/app/registry.py` — Add `themes` to `ResolvedRegistry`, update `build_registry()` with built-in themes
- `src/continuum/app/runtime.py` — Add `themes` to `RegistryState`, add `get_themes()`
- `src/continuum/adapters/web/api.py` — Add `themes` to `RegistryResponse`
- `web/src/lib/stores/registry.ts` — Add `themes` to `Registry` interface, add derived stores
- `web/src/lib/components/Shell.svelte` — Add `restoreTheme()` call, event listener, `<ThemeSelector>` in footer
- `web/src/app.html` — Add inline FOUC prevention script (5 lines)

### Core Framework (Created)

- `src/continuum/domain/themes.py` — Built-in theme definitions (Light, High Contrast)
- `web/src/lib/services/themeEngine.ts` — Theme application engine
- `web/src/lib/components/ThemeSelector.svelte` — Compact footer theme selector

### Plugin (Created)

- `plugins/continuum.theme_selector/plugin.toml`
- `plugins/continuum.theme_selector/__init__.py`
- `plugins/continuum.theme_selector/ui/package.json`
- `plugins/continuum.theme_selector/ui/vite.config.js`
- `plugins/continuum.theme_selector/ui/src/index.js`
- `plugins/continuum.theme_selector/ui/src/ThemeSelector.svelte`

### Tests (Created)

- `tests/test_theme_contributions.py`
- `tests/test_theme_plugin.py`

---

## Implementation Order

```
Phase 1    Core theme seam — backend (contribution type, registry, API)
Phase 2    Core theme seam — frontend (engine, stores, Shell integration, FOUC)
Phase 3    Theme selector plugin (theme pack + picker UI)
Phase 4    Testing & polish
```

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

### Plugin
- [ ] Plugin discovered and loaded by `continuum inspect`
- [ ] 3 plugin themes appear in `/api/registry` alongside 2 built-ins
- [ ] Theme selector drawer opens from "Appearance" nav item
- [ ] Drawer shows all 6 themes (default + 2 built-in + 3 contributed) with swatches
- [ ] Themes grouped as "Built-in" and "Theme Pack" in drawer
- [ ] Clicking a theme card applies it instantly
- [ ] Active theme shows checkmark indicator
- [ ] "Reset to Default" removes theme and reverts to shell defaults
- [ ] Plugin bundle builds with `./scripts/build-plugins.sh`
- [ ] Removing the plugin leaves 3 built-in themes still working

### Integration
- [ ] Existing plugin panels (Signal, Systems, etc.) recolor correctly
- [ ] No functionality regression — navigation, commands, drawers all work
- [ ] Light theme has appropriate shadow adjustments
- [ ] High contrast theme uses maximum contrast ratios
- [ ] A second hypothetical plugin contributing `[[contributions.theme]]` would work
