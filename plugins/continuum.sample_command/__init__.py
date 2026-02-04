"""
Continuum Sample Command Plugin - Command contributions.

Provides command contributions:
- Open command palette (Ctrl+K)
- Sample action (Ctrl+Shift+S)
"""


def register(ctx):
    """Register plugin contributions."""
    ctx.register_contribution("command", {
        "id": "open_command_palette",
        "label": "Open Command Palette",
        "icon": "terminal",
        "shortcut": "Ctrl+K",
        "action": "open_command_palette",
    })

    ctx.register_contribution("command", {
        "id": "sample_action",
        "label": "Sample Action",
        "icon": "play",
        "shortcut": "Ctrl+Shift+S",
        "action": "sample_action",
    })
