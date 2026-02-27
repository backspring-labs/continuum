# Plan: Theme Selector Plugin

**Date:** 2026-02-27
**Status:** Draft (v1.0)
**Reference:** `CONTINUUM_V1_ARCH_SPEC.md`, `002-dynamic-plugin-ui-loading.md`

---

## Overview

Add a **theme selector** distributed as a Continuum plugin (`continuum.theme_selector`) that lets operators switch the visual appearance of the entire dashboard without impacting any functionality. The plugin ships with a curated **theme pack** (multiple pre-built themes) and provides the infrastructure for plugins or host apps to register additional themes in the future.

### Design Principles

1. **CSS Custom Properties are the contract** — Continuum already defines all visual tokens as `--continuum-*` CSS custom properties in `app.css`. Themes are simply alternate sets of these token values. No structural HTML or component changes needed.
2. **Plugin, not core** — The theme system lives entirely in the plugin. The shell's `app.css` continues to define the default (dark) theme. The plugin overrides token values at runtime via a `<style>` element or class-scoped CSS.
3. **Zero functionality impact** — Themes only change CSS custom property values. Layout, navigation, plugin rendering, commands, and all other behavior remain untouched.
4. **Persistence** — Selected theme is stored in `localStorage` and restored on page load, so operators keep their preference across sessions.
5. **Host-friendly** — Follows Continuum's plugin model: drop in the plugin, restart, theme selector appears.

---

## End State Definition

> Open the dashboard → click theme selector in footer/drawer → pick a theme → entire UI recolors instantly.
> Refresh → theme persists. Remove the plugin → dashboard reverts to default dark theme.

---

## Architecture

### How Theming Works

```
app.css (shell)                     Theme Plugin
┌─────────────────────┐             ┌───────────────────────────┐
│ :root {             │             │ [data-theme="midnight"] { │
│   --continuum-bg-*  │  overrides  │   --continuum-bg-*: ...   │
│   --continuum-text-*│ ◄────────── │   --continuum-text-*: ... │
│   ...               │             │   ...                     │
│ }                   │             │ }                         │
└─────────────────────┘             └───────────────────────────┘
```

1. Shell defines tokens on `:root` (current behavior, unchanged)
2. Theme plugin adds a `data-theme` attribute to `<html>` element
3. Theme CSS uses `[data-theme="name"]` selectors to override token values
4. CSS specificity ensures theme overrides win over `:root` defaults
5. When no theme is active (plugin removed), `:root` defaults apply — graceful fallback

### Token Categories Themed

All existing `--continuum-*` tokens are fair game for theming:

| Category | Token Pattern | Example |
|----------|---------------|---------|
| Backgrounds | `--continuum-bg-*` | `--continuum-bg-primary`, `--continuum-bg-secondary` |
| Text | `--continuum-text-*` | `--continuum-text-primary`, `--continuum-text-muted` |
| Accents | `--continuum-accent-*` | `--continuum-accent-primary`, `--continuum-accent-danger` |
| Borders | `--continuum-border*` | `--continuum-border`, `--continuum-border-muted` |
| Shadows | `--continuum-shadow-*` | `--continuum-shadow-sm`, `--continuum-shadow-lg` |
| Radii | `--continuum-radius-*` | `--continuum-radius-sm`, `--continuum-radius-md` |

Layout tokens (`--continuum-nav-width`, `--continuum-header-height`) are intentionally **excluded** from theming to preserve structural consistency.

### Theme Definition Format

Each theme is a named set of token overrides:

```typescript
interface Theme {
  id: string;            // e.g., "midnight", "light", "nord"
  name: string;          // Display name: "Midnight Blue"
  description: string;   // Short description
  category: 'dark' | 'light';  // For grouping in UI
  tokens: Record<string, string>;  // CSS custom property values
}
```

Themes are defined as static data within the plugin — no backend involvement required.

---

## Theme Pack (Shipped Themes)

### 1. Default Dark (built-in)
The existing `app.css` theme. Not defined in the plugin — this is what you get when no theme is selected (or plugin is removed).

### 2. Midnight Blue (`midnight`)
- Deep navy backgrounds (`#0b1628`, `#111d35`)
- Blue-tinted text hierarchy
- Electric blue accents
- Category: dark

### 3. Light (`light`)
- White/light gray backgrounds (`#ffffff`, `#f6f8fa`)
- Dark text (`#1f2328`, `#656d76`)
- Blue accents matching GitHub light
- Adjusted shadows (lighter, less opacity)
- Category: light

### 4. Nord (`nord`)
- Arctic, bluish-gray backgrounds from Nord palette (`#2e3440`, `#3b4252`)
- Cool-toned text (`#eceff4`, `#d8dee9`)
- Frost blue accents (`#88c0d0`, `#81a1c1`)
- Category: dark

### 5. Solarized Dark (`solarized-dark`)
- Classic Solarized dark backgrounds (`#002b36`, `#073642`)
- Solarized text hierarchy (`#839496`, `#93a1a1`)
- Solarized accent colors (yellow `#b58900`, blue `#268bd2`)
- Category: dark

### 6. High Contrast (`high-contrast`)
- Pure black background (`#000000`, `#0a0a0a`)
- Pure white text (`#ffffff`, `#f0f0f0`)
- Bright, saturated accent colors
- Enhanced borders for visibility
- Category: dark
- Accessibility-focused

---

## Plugin Structure

```
plugins/
  continuum.theme_selector/
    plugin.toml                    # Manifest
    __init__.py                    # Python entrypoint (minimal)
    ui/
      src/
        ThemeSelector.svelte       # Drawer panel: theme picker UI
        ThemeProvider.svelte        # Headless component: applies theme on load
        themes/
          index.ts                 # Theme registry (all theme definitions)
          midnight.ts              # Midnight Blue theme tokens
          light.ts                 # Light theme tokens
          nord.ts                  # Nord theme tokens
          solarized-dark.ts        # Solarized Dark theme tokens
          high-contrast.ts         # High Contrast theme tokens
        lib/
          theme-engine.ts          # Core: apply/remove theme, localStorage
        index.js                   # Bundle entry point
      vite.config.js
    dist/
      plugin.js                    # Built Web Component bundle
```

### Manifest (`plugin.toml`)

```toml
[plugin]
id = "continuum.theme_selector"
name = "Theme Selector"
version = "1.0.0"
description = "Visual theme selector with built-in theme pack for the Continuum dashboard"
required = false

[plugin.ui]
tag_prefix = "continuum-theme-selector"
bundle = "plugin.js"

# Drawer contribution: the theme picker panel
[[contributions.drawer]]
id = "theme_selector"
component = "continuum-theme-selector-picker"
title = "Appearance"
width = "360px"

# Nav contribution: button to open theme selector drawer
[[contributions.nav]]
slot = "ui.slot.left_nav"
label = "Appearance"
icon = "palette"
priority = 10

[contributions.nav.target]
type = "drawer"
drawer_id = "theme_selector"

# Panel contribution: headless theme provider (applies saved theme on load)
[[contributions.panel]]
slot = "ui.slot.footer"
component = "continuum-theme-selector-provider"
priority = 1
```

### Python Entrypoint (`__init__.py`)

```python
"""
Continuum Theme Selector Plugin - Visual theme switcher with theme pack.

Provides:
- Drawer panel for selecting themes
- Headless provider component that restores saved theme on load
- Nav item to open theme selector
"""


def register(ctx):
    """Register plugin contributions."""
    ctx.register_contribution("drawer", {
        "id": "theme_selector",
        "component": "continuum-theme-selector-picker",
        "title": "Appearance",
        "width": "360px",
    })

    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Appearance",
        "icon": "palette",
        "priority": 10,
        "target": {"type": "drawer", "drawer_id": "theme_selector"},
    })

    ctx.register_contribution("panel", {
        "slot": "ui.slot.footer",
        "component": "continuum-theme-selector-provider",
        "priority": 1,
    })
```

---

## Component Design

### ThemeProvider (`continuum-theme-selector-provider`)

A headless Web Component (renders nothing visible) that:

1. On mount, reads `localStorage.getItem('continuum-theme')`
2. If a theme ID is found, applies it immediately (prevents flash of default theme)
3. Listens for `continuum:theme-change` custom events from the picker
4. Applies theme by:
   - Setting `document.documentElement.dataset.theme = themeId`
   - Injecting/updating a `<style id="continuum-theme-overrides">` element with theme token values
5. On disconnect, optionally cleans up (though theme persists)

**Why inject `<style>` instead of just `data-theme` + static CSS?**
- Theme definitions are in TypeScript/JS, not in a static CSS file
- This allows future dynamic theme registration without rebuilding
- The `<style>` element approach works regardless of Shadow DOM configuration
- Fallback: if JS fails, `:root` defaults still apply

```typescript
// theme-engine.ts (core logic)
const STORAGE_KEY = 'continuum-theme';
const STYLE_ID = 'continuum-theme-overrides';

export function applyTheme(theme: Theme | null): void {
  const el = document.documentElement;
  const existing = document.getElementById(STYLE_ID);

  if (!theme) {
    // Remove theme — revert to defaults
    delete el.dataset.theme;
    existing?.remove();
    localStorage.removeItem(STORAGE_KEY);
    return;
  }

  // Set data attribute for CSS selectors
  el.dataset.theme = theme.id;

  // Build CSS override block
  const css = `[data-theme="${theme.id}"] {\n` +
    Object.entries(theme.tokens)
      .map(([prop, value]) => `  ${prop}: ${value};`)
      .join('\n') +
    '\n}';

  // Inject or update style element
  if (existing) {
    existing.textContent = css;
  } else {
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = css;
    document.head.appendChild(style);
  }

  // Persist selection
  localStorage.setItem(STORAGE_KEY, theme.id);
}

export function getStoredThemeId(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}
```

### ThemeSelector (`continuum-theme-selector-picker`)

A drawer panel Web Component that displays:

1. **Theme grid** — Card per theme showing:
   - Theme name
   - Category badge (dark/light)
   - Color swatch preview (4-5 sample colors from the theme tokens)
   - Active indicator (checkmark) for current selection
2. **"Reset to Default"** button — removes theme, reverts to shell defaults
3. **Live preview** — Selecting a theme applies it immediately (no separate confirm step)

```
┌─ Appearance ────────────────────────┐
│                                      │
│  Choose a theme for your dashboard   │
│                                      │
│  ┌──────────┐  ┌──────────┐         │
│  │ ████████ │  │ ████████ │         │
│  │ Default  │  │ Midnight │         │
│  │ Dark   ✓ │  │ Blue     │         │
│  └──────────┘  └──────────┘         │
│                                      │
│  ┌──────────┐  ┌──────────┐         │
│  │ ░░░░░░░░ │  │ ████████ │         │
│  │ Light    │  │ Nord     │         │
│  │          │  │          │         │
│  └──────────┘  └──────────┘         │
│                                      │
│  ┌──────────┐  ┌──────────┐         │
│  │ ████████ │  │ ████████ │         │
│  │ Solarized│  │ High     │         │
│  │ Dark     │  │ Contrast │         │
│  └──────────┘  └──────────┘         │
│                                      │
│  [Reset to Default]                  │
│                                      │
└──────────────────────────────────────┘
```

**Interaction flow:**
1. User clicks "Appearance" nav item → drawer slides in
2. Current theme is highlighted
3. Click a theme card → theme applies instantly
4. Close drawer → theme persists
5. Refresh → ThemeProvider restores theme before first paint

---

## Implementation Phases

### Phase 1: Theme Engine & Provider (Foundation)

**Goal:** Theme application infrastructure works end-to-end.

**Files to create:**
- `plugins/continuum.theme_selector/ui/src/lib/theme-engine.ts` — `applyTheme()`, `getStoredThemeId()`, theme type definitions
- `plugins/continuum.theme_selector/ui/src/themes/index.ts` — Theme registry, exports all themes
- `plugins/continuum.theme_selector/ui/src/themes/midnight.ts` — First theme definition
- `plugins/continuum.theme_selector/ui/src/ThemeProvider.svelte` — Headless custom element

**Verification:**
- Manually calling `applyTheme(midnightTheme)` in console recolors the dashboard
- Refreshing the page restores the theme before content renders
- Calling `applyTheme(null)` reverts to defaults cleanly
- All existing plugin panels and shell components recolor correctly (they already use `var(--continuum-*)`)

### Phase 2: Theme Pack (Content)

**Goal:** All six themes defined and visually polished.

**Files to create:**
- `plugins/continuum.theme_selector/ui/src/themes/light.ts`
- `plugins/continuum.theme_selector/ui/src/themes/nord.ts`
- `plugins/continuum.theme_selector/ui/src/themes/solarized-dark.ts`
- `plugins/continuum.theme_selector/ui/src/themes/high-contrast.ts`

**Verification:**
- Each theme applies cleanly — no unthemed elements visible
- Light theme has appropriate shadow adjustments (lighter shadows vs dark themes)
- High contrast theme passes basic contrast ratio checks
- Scrollbar styling adapts (`::-webkit-scrollbar` uses token values)

**Note on scrollbar theming:**
The shell's `app.css` uses direct color values for scrollbars (`::-webkit-scrollbar-track`, etc.). Phase 2 should either:
- (a) Refactor shell scrollbar styles to use `var(--continuum-*)` tokens (preferred, minimal change), or
- (b) Have the theme engine inject scrollbar overrides alongside token overrides

Option (a) is preferred as it makes the shell more theme-ready with a one-line change and benefits all future themes.

### Phase 3: Selector UI (Drawer Component)

**Goal:** Full theme picker UI in a drawer panel.

**Files to create:**
- `plugins/continuum.theme_selector/ui/src/ThemeSelector.svelte` — Theme picker drawer
- `plugins/continuum.theme_selector/ui/src/index.js` — Bundle entry point

**Verification:**
- Drawer opens from nav item click
- All themes display as cards with preview swatches
- Clicking a theme applies it immediately
- Active theme shows checkmark indicator
- "Reset to Default" button works
- Drawer closes normally; theme persists

### Phase 4: Plugin Packaging & Integration

**Goal:** Ship as a complete, installable Continuum plugin.

**Files to create:**
- `plugins/continuum.theme_selector/plugin.toml`
- `plugins/continuum.theme_selector/__init__.py`
- `plugins/continuum.theme_selector/ui/vite.config.js`
- `plugins/continuum.theme_selector/ui/package.json`

**Build & verify:**
- `cd plugins/continuum.theme_selector/ui && npm install && npm run build`
- `./scripts/build-plugins.sh` includes theme selector
- `continuum inspect` shows the plugin as loaded
- Full end-to-end: boot server → open dashboard → click Appearance → switch themes

### Phase 5: Testing & Polish

**Goal:** Confidence that themes don't break anything.

**Tests to add:**
- `tests/test_theme_plugin.py` — Plugin discovery, manifest validation, asset serving
- Theme engine unit tests (apply, remove, persist, restore)
- Visual regression: screenshot each theme (manual or Playwright)

**Polish:**
- Smooth CSS transitions when switching themes (`transition: background-color var(--continuum-transition-normal), color var(--continuum-transition-normal)`)
- Theme preview tooltip on hover (before committing to click)
- Keyboard navigation within theme grid (arrow keys + enter)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Plugin Web Components use Shadow DOM and don't inherit tokens | V1 uses Shadow DOM OFF (`shadow: 'none'`). Tokens propagate via CSS inheritance. If shadow DOM is enabled later, CSS custom properties still cross shadow boundaries. |
| Flash of default theme on page load | ThemeProvider is loaded in the footer slot (always present). It runs `applyTheme()` synchronously on mount, before other panels render. For critical FOUC prevention, consider a `<script>` in `app.html` that reads localStorage and sets `data-theme` before Svelte hydrates. |
| Theme CSS specificity conflicts | `[data-theme="x"]` selector has higher specificity than `:root`, so overrides win naturally. No `!important` needed. |
| Removing the plugin leaves stale `data-theme` attribute | The default `:root` tokens still apply. `[data-theme]` selectors only match when the theme plugin has injected its style block. Without the style block, the attribute is inert. Harmless. |
| Third-party plugin uses hardcoded colors instead of tokens | This is a plugin authoring issue, not a theme system issue. Document in plugin development guide that plugins MUST use `var(--continuum-*)` tokens for theme compatibility. |

---

## FOUC Prevention Strategy

Flash of unstyled content (showing default dark theme before saved theme applies) is the primary UX concern.

**Primary approach:** Add a small inline script to `web/src/app.html`:

```html
<script>
  // Apply saved theme before any rendering (FOUC prevention)
  const t = localStorage.getItem('continuum-theme');
  if (t) document.documentElement.dataset.theme = t;
</script>
```

This sets the `data-theme` attribute synchronously during page load. The theme plugin's injected `<style>` block arrives shortly after (when the plugin bundle loads), completing the theme application. The brief window between `data-theme` being set and the `<style>` injection is handled by having a static CSS file with all theme definitions as a fallback.

**Fallback for the fallback:** Even without the inline script, the ThemeProvider applies the theme as soon as it mounts. The flash duration depends on plugin bundle load time (typically <100ms on localhost).

---

## Future Extensions (Not in This Plan)

- **Custom themes** — Let operators define their own token overrides via a theme editor UI
- **Theme API** — Backend endpoint to store themes per-user (instead of localStorage)
- **Theme SDK** — Allow other plugins to register themes (e.g., a brand-specific theme pack)
- **Scheduling** — Auto-switch between light/dark based on time of day or OS preference
- **`prefers-color-scheme` media query** — Respect OS dark/light mode setting as default
- **Per-perspective themes** — Different theme per perspective (e.g., dark for Signal, light for Research)

---

## Files Modified/Created Summary

**Create:**
- `plugins/continuum.theme_selector/plugin.toml`
- `plugins/continuum.theme_selector/__init__.py`
- `plugins/continuum.theme_selector/ui/package.json`
- `plugins/continuum.theme_selector/ui/vite.config.js`
- `plugins/continuum.theme_selector/ui/src/index.js`
- `plugins/continuum.theme_selector/ui/src/ThemeProvider.svelte`
- `plugins/continuum.theme_selector/ui/src/ThemeSelector.svelte`
- `plugins/continuum.theme_selector/ui/src/lib/theme-engine.ts`
- `plugins/continuum.theme_selector/ui/src/themes/index.ts`
- `plugins/continuum.theme_selector/ui/src/themes/midnight.ts`
- `plugins/continuum.theme_selector/ui/src/themes/light.ts`
- `plugins/continuum.theme_selector/ui/src/themes/nord.ts`
- `plugins/continuum.theme_selector/ui/src/themes/solarized-dark.ts`
- `plugins/continuum.theme_selector/ui/src/themes/high-contrast.ts`
- `tests/test_theme_plugin.py`

**Modify (minimal):**
- `web/src/app.css` — Refactor scrollbar styles to use `var(--continuum-*)` tokens (3 lines)
- `web/src/app.html` — Add inline FOUC prevention script (4 lines, optional)

**No modifications to:**
- Shell components (Shell.svelte, RegionSlot.svelte, etc.)
- Registry store or API
- Other plugins
- Backend runtime or registry

---

## Implementation Order

```
Phase 1    Theme engine + provider (foundation)
Phase 2    Theme pack (all 6 themes)
Phase 3    Selector UI (drawer component)
Phase 4    Plugin packaging & integration
Phase 5    Testing & polish
```

---

## Verification Checklist

- [ ] Theme engine `applyTheme()` overrides all `--continuum-*` tokens
- [ ] `applyTheme(null)` cleanly reverts to shell defaults
- [ ] Theme persists in `localStorage` across page refreshes
- [ ] ThemeProvider restores saved theme before visible content renders
- [ ] All 6 themes display correctly with no unthemed elements
- [ ] Light theme adjusts shadows and borders appropriately
- [ ] High contrast theme uses maximum contrast ratios
- [ ] Theme selector drawer opens from nav item
- [ ] Theme cards show color swatch previews
- [ ] Active theme shows checkmark indicator
- [ ] "Reset to Default" removes theme and reverts to shell defaults
- [ ] Plugin discovered and loaded by `continuum inspect`
- [ ] Plugin bundle builds with `./scripts/build-plugins.sh`
- [ ] Removing the plugin directory reverts dashboard to default theme
- [ ] Existing plugin panels (Signal, Systems, etc.) recolor correctly
- [ ] No functionality regression — navigation, commands, drawers all work
- [ ] Scrollbar styling adapts to theme
