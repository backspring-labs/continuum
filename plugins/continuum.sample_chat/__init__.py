"""
Continuum Sample Chat Plugin - Agent chat drawer.

Provides a drawer contribution for the agent chat interface.
"""


def register(ctx):
    """Register plugin contributions."""
    ctx.register_contribution("drawer", {
        "id": "agent_chat",
        "slot": "ui.slot.drawer",
        "component": "continuum-sample-chat-drawer",
        "title": "Agent Chat",
        "width": "400px",
    })
