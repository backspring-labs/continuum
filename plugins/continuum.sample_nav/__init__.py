"""
Continuum Sample Nav Plugin - Navigation contributions.

Provides nav contributions for:
- Perspective switchers (Signal, Research, Time, Discovery, Systems)
"""


def register(ctx):
    """Register plugin contributions."""
    # Perspective switchers - highest priority shows first
    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Signal",
        "icon": "activity",
        "target": {"type": "panel", "panel_id": "signal"},
        "priority": 500,
    })

    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Research",
        "icon": "search",
        "target": {"type": "panel", "panel_id": "research"},
        "priority": 400,
    })

    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Time",
        "icon": "clock",
        "target": {"type": "panel", "panel_id": "time"},
        "priority": 300,
    })

    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Discovery",
        "icon": "compass",
        "target": {"type": "panel", "panel_id": "discovery"},
        "priority": 200,
    })

    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Systems",
        "icon": "settings",
        "target": {"type": "panel", "panel_id": "systems"},
        "priority": 100,
    })
