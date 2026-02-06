"""
Continuum Sample Command Plugin - Command contributions.

Demonstrates the full command contribution API including:
- Basic commands (safe)
- Confirmation-required commands (confirm)
- Dangerous commands (danger)
- Dry run support
- Input schema validation
- Audit redaction
"""


def register(ctx):
    """Register plugin contributions."""
    # Client-side command: opens the command palette
    ctx.register_contribution("command", {
        "id": "open_command_palette",
        "label": "Open Command Palette",
        "icon": "terminal",
        "shortcut": "Ctrl+K",
        "action": "open_command_palette",
        "danger_level": "safe",
    })

    # Basic safe command with handler
    ctx.register_contribution("command", {
        "id": "sample_action",
        "label": "Sample Action",
        "icon": "play",
        "shortcut": "Ctrl+Shift+S",
        "action": "sample_action",
        "danger_level": "safe",
        "dry_run_supported": True,
    })

    # Echo command with input schema validation
    ctx.register_contribution("command", {
        "id": "echo",
        "label": "Echo Message",
        "icon": "message",
        "action": "echo",
        "danger_level": "safe",
        "dry_run_supported": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "minLength": 1},
            },
            "required": ["message"],
        },
    })

    # Confirmation-level command (requires user to confirm)
    ctx.register_contribution("command", {
        "id": "restart_service",
        "label": "Restart Service",
        "icon": "refresh",
        "action": "restart_service",
        "danger_level": "confirm",
        "dry_run_supported": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
            },
            "required": ["service_name"],
        },
    })

    # Danger-level command (requires explicit confirmation, no Enter key)
    ctx.register_contribution("command", {
        "id": "clear_cache",
        "label": "Clear All Caches",
        "icon": "trash",
        "action": "clear_cache",
        "danger_level": "danger",
        "dry_run_supported": True,
    })

    # Command with audit redaction (sensitive args hidden in logs)
    ctx.register_contribution("command", {
        "id": "update_secret",
        "label": "Update Secret",
        "icon": "lock",
        "action": "update_secret",
        "danger_level": "confirm",
        "audit_redaction": ["secret_value", "password"],
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "secret_value": {"type": "string"},
            },
            "required": ["key", "secret_value"],
        },
    })

    # Command requiring specific capabilities
    ctx.register_contribution("command", {
        "id": "deploy_production",
        "label": "Deploy to Production",
        "icon": "rocket",
        "action": "deploy",
        "danger_level": "danger",
        "required_capabilities": ["deploy.production"],
        "dry_run_supported": True,
    })
