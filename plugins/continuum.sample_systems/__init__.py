"""
Continuum Sample Systems Plugin - System administration dashboard.

Provides panel contributions for the Systems perspective:
- Plugins panel (shows plugin status)
- Registry panel (shows registry contents)
- Diagnostics panel in right rail
"""


def register(ctx):
    """Register plugin contributions."""
    # Plugins panel - shows plugin status
    ctx.register_contribution("panel", {
        "slot": "ui.slot.main",
        "perspective": "systems",
        "component": "continuum-sample-systems-plugins",
        "priority": 200,
    })

    # Registry panel - shows resolved registry
    ctx.register_contribution("panel", {
        "slot": "ui.slot.main",
        "perspective": "systems",
        "component": "continuum-sample-systems-registry",
        "priority": 100,
    })

    # Diagnostics panel in right rail
    ctx.register_contribution("panel", {
        "slot": "ui.slot.right_rail",
        "perspective": "systems",
        "component": "continuum-sample-systems-diagnostics",
        "priority": 100,
    })
