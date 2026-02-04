"""
Continuum Sample Signal Plugin - Signal monitoring dashboard.

Provides panel contributions for the Signal perspective:
- Metrics panel (high priority)
- Timeline panel (lower priority)
- Alerts panel in right rail
"""


def register(ctx):
    """Register plugin contributions."""
    # Metrics panel - high priority, shows first
    ctx.register_contribution("panel", {
        "slot": "ui.slot.main",
        "perspective": "signal",
        "component": "continuum-sample-signal-metrics",
        "priority": 200,
    })

    # Timeline panel - lower priority
    ctx.register_contribution("panel", {
        "slot": "ui.slot.main",
        "perspective": "signal",
        "component": "continuum-sample-signal-timeline",
        "priority": 100,
    })

    # Alerts panel in right rail
    ctx.register_contribution("panel", {
        "slot": "ui.slot.right_rail",
        "perspective": "signal",
        "component": "continuum-sample-signal-alerts",
        "priority": 100,
    })
