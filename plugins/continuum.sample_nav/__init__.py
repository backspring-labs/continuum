"""
Continuum Sample Nav Plugin - Navigation contributions.

Provides nav contributions for:
- Perspective switchers (Signal, Research, Time, Discovery, Systems)
- Action triggers (Command palette, Agent chat)
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

    # Action triggers - lower priority, shown after perspectives
    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Commands",
        "icon": "terminal",
        "target": {"type": "command", "command_id": "open_command_palette"},
        "priority": 50,
    })

    ctx.register_contribution("nav", {
        "slot": "ui.slot.left_nav",
        "label": "Chat",
        "icon": "message-circle",
        "target": {"type": "drawer", "drawer_id": "agent_chat"},
        "priority": 40,
    })
