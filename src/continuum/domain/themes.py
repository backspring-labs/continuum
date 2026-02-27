"""
Built-in theme definitions and token contract.

The core framework ships three built-in themes so theming works immediately
with zero plugins installed. Plugins can contribute additional themes via
[[contributions.theme]], or override a built-in by contributing a theme
with the same ID.

All themes (built-in and plugin-contributed) must provide every token in
REQUIRED_THEME_TOKENS. Incomplete themes are rejected during registry build.
"""

# The canonical set of CSS custom properties that every theme must define.
# These are the color/shadow tokens from app.css :root. Structural tokens
# (spacing, typography, layout, radius, transitions) are NOT themeable.
REQUIRED_THEME_TOKENS: tuple[str, ...] = (
    "--continuum-bg-primary",
    "--continuum-bg-secondary",
    "--continuum-bg-tertiary",
    "--continuum-bg-hover",
    "--continuum-bg-active",
    "--continuum-border",
    "--continuum-border-muted",
    "--continuum-text-primary",
    "--continuum-text-secondary",
    "--continuum-text-muted",
    "--continuum-text-link",
    "--continuum-accent-primary",
    "--continuum-accent-success",
    "--continuum-accent-warning",
    "--continuum-accent-danger",
    "--continuum-shadow-sm",
    "--continuum-shadow-md",
    "--continuum-shadow-lg",
)

# Reserved built-in theme IDs. Plugins may override these, but third-party
# plugins should use namespaced IDs (e.g. "squadops-dark").
BUILTIN_THEME_IDS: frozenset[str] = frozenset({
    "default-dark",
    "light",
    "high-contrast",
})

BUILTIN_THEMES: list[dict] = [
    {
        "id": "default-dark",
        "name": "Default Dark",
        "description": "The default Continuum dark theme",
        "category": "dark",
        "builtin": True,
        "tags": [],
        "preview_colors": ["#0d1117", "#161b22", "#58a6ff", "#e6edf3", "#3fb950"],
        "tokens": {
            "--continuum-bg-primary": "#0d1117",
            "--continuum-bg-secondary": "#161b22",
            "--continuum-bg-tertiary": "#21262d",
            "--continuum-bg-hover": "#30363d",
            "--continuum-bg-active": "#388bfd33",
            "--continuum-border": "#30363d",
            "--continuum-border-muted": "#21262d",
            "--continuum-text-primary": "#e6edf3",
            "--continuum-text-secondary": "#8b949e",
            "--continuum-text-muted": "#6e7681",
            "--continuum-text-link": "#58a6ff",
            "--continuum-accent-primary": "#58a6ff",
            "--continuum-accent-success": "#3fb950",
            "--continuum-accent-warning": "#d29922",
            "--continuum-accent-danger": "#f85149",
            "--continuum-shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.3)",
            "--continuum-shadow-md": "0 4px 12px rgba(0, 0, 0, 0.4)",
            "--continuum-shadow-lg": "0 8px 24px rgba(0, 0, 0, 0.5)",
        },
    },
    {
        "id": "light",
        "name": "Light",
        "description": "Clean light theme for bright environments",
        "category": "light",
        "builtin": True,
        "tags": [],
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
        "tags": ["accessibility"],
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


import re

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def validate_theme(theme: dict) -> list[str]:
    """
    Validate a theme dict against the token contract.

    Returns a list of error strings. Empty list means valid.
    """
    errors: list[str] = []
    theme_id = theme.get("id", "<unknown>")

    # Check required token completeness
    provided_tokens = set(theme.get("tokens", {}).keys())
    required = set(REQUIRED_THEME_TOKENS)
    missing = required - provided_tokens
    if missing:
        errors.append(
            f"Theme '{theme_id}' missing required tokens: {', '.join(sorted(missing))}"
        )

    # Check that all token keys use --continuum- prefix
    for key in provided_tokens:
        if not key.startswith("--continuum-"):
            errors.append(
                f"Theme '{theme_id}' has non-prefixed token '{key}' "
                f"(all tokens must start with '--continuum-')"
            )

    # Validate category
    category = theme.get("category", "")
    if category not in ("dark", "light"):
        errors.append(f"Theme '{theme_id}' has invalid category '{category}' (must be 'dark' or 'light')")

    # Validate preview_colors: 3-5 hex color strings
    colors = theme.get("preview_colors", [])
    if not isinstance(colors, list) or not (3 <= len(colors) <= 5):
        errors.append(
            f"Theme '{theme_id}' must have 3-5 preview_colors, got {len(colors) if isinstance(colors, list) else 0}"
        )
    else:
        for color in colors:
            if not isinstance(color, str) or not _HEX_COLOR_RE.match(color):
                errors.append(
                    f"Theme '{theme_id}' has invalid preview_color '{color}' (must be #rgb or #rrggbb)"
                )

    return errors
