"""
Continuum Sample Diagnostics Plugin - Diagnostic contributions.

Provides diagnostic contributions for health checking.
"""


def register(ctx):
    """Register plugin contributions."""
    ctx.register_contribution("diagnostic", {
        "id": "sample_health",
        "slot": "ui.slot.toast_stack",
        "label": "Sample Health Check",
        "check": "sample_health_check",
    })
