# Command Contribution Guide

This guide covers how to create commands in Continuum, including permission models, danger levels, audit logging, and handler implementation.

## Command Registration

Commands are registered via the plugin contribution system. You can define them in `plugin.toml` or programmatically in `__init__.py`.

### TOML Registration

```toml
[[contributions.command]]
id = "my_command"
label = "My Command"
icon = "play"
shortcut = "Ctrl+Shift+M"
action = "my_handler"
danger_level = "safe"
```

### Python Registration

```python
def register(ctx):
    ctx.register_contribution("command", {
        "id": "my_command",
        "label": "My Command",
        "icon": "play",
        "shortcut": "Ctrl+Shift+M",
        "action": "my_handler",
        "danger_level": "safe",
        "dry_run_supported": True,
    })
```

## Command Properties

| Property | Required | Description |
|----------|----------|-------------|
| `id` | Yes | Unique identifier for the command |
| `label` | Yes | Display name shown in UI |
| `action` | Yes | Handler action name (maps to registered handler) |
| `icon` | No | Lucide icon name |
| `shortcut` | No | Keyboard shortcut (e.g., "Ctrl+K", "Ctrl+Shift+S") |
| `danger_level` | No | `safe`, `confirm`, or `danger` (default: `safe`) |
| `required_capabilities` | No | List of capabilities user must have |
| `audit_redaction` | No | List of argument keys to redact in audit logs |
| `dry_run_supported` | No | Whether command supports preview mode |
| `input_schema` | No | JSON Schema for argument validation |
| `timeout_ms` | No | Execution timeout in milliseconds (default: 30000) |

## Danger Levels

Danger levels provide UI guardrails to prevent accidental execution of destructive operations.

### Safe (default)
```python
"danger_level": "safe"
```
- Executes immediately when triggered
- No confirmation required
- Use for: read-only operations, non-destructive actions

**Examples:** Open command palette, echo message, view status

### Confirm
```python
"danger_level": "confirm"
```
- Requires user confirmation before execution
- Shows confirmation dialog with command details
- Use for: operations that modify state but are reversible

**Examples:** Restart service, clear session, update configuration

### Danger
```python
"danger_level": "danger"
```
- Requires explicit confirmation (cannot be bypassed with Enter key)
- Shows prominent warning in confirmation dialog
- Use for: destructive or irreversible operations

**Examples:** Clear all caches, delete data, deploy to production

## Capabilities and Permissions

Commands can require specific capabilities for authorization.

### Defining Required Capabilities

```python
ctx.register_contribution("command", {
    "id": "deploy_production",
    "label": "Deploy to Production",
    "action": "deploy",
    "danger_level": "danger",
    "required_capabilities": ["deploy.production"],
})
```

### How Authorization Works

1. Command is executed
2. PolicyEngine evaluates user capabilities against required capabilities
3. If user lacks any required capability, execution is **denied**
4. Denial is logged in audit with rationale

```python
# User context with capabilities
user = UserContext(
    user_id="alice",
    capabilities=("deploy.staging", "view.metrics"),
)

# Command requires deploy.production
# Result: DENIED - "Missing required capabilities: deploy.production"
```

### Capability Naming Convention

Use dot-notation for capability hierarchies:

```
resource.action
└── deploy.production
└── deploy.staging
└── view.metrics
└── admin.users.create
```

### Wildcard Capability

The `*` capability grants access to all commands:

```python
# System user has all capabilities
user = UserContext.system()  # capabilities=("*",)
```

**Note:** In V1, the mock operator user has `capabilities=("*",)`. Real authorization will be implemented in V2.

## Audit Logging

All command executions are logged for compliance and debugging.

### What Gets Logged

Every execution creates an `AuditEntry` with:
- `audit_id` - Unique identifier
- `command_id` - Which command was executed
- `user_id` - Who executed it
- `timestamp` - When it was executed (ISO format)
- `status` - `success`, `failed`, `denied`, `pending`, `timeout`
- `duration_ms` - Execution time
- `args_redacted` - Arguments with sensitive values redacted
- `error` - Error message if failed/denied
- `context` - Additional context (request_id, etc.)

### Argument Redaction

Sensitive arguments should never appear in audit logs. Define redaction keys:

```python
ctx.register_contribution("command", {
    "id": "update_secret",
    "label": "Update Secret",
    "action": "update_secret",
    "danger_level": "confirm",
    "audit_redaction": ["secret_value", "password", "api_key"],
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "secret_value": {"type": "string"},
        },
    },
})
```

**In audit log:**
```json
{
  "command_id": "update_secret",
  "args_redacted": {
    "key": "database_password",
    "secret_value": "[REDACTED]"
  }
}
```

### Viewing Audit Logs

```bash
# Via API
curl http://localhost:4040/api/commands/audit?limit=50

# In UI
# Navigate to Systems > Audit panel
```

## Input Validation

Commands can define JSON Schema for argument validation:

```python
ctx.register_contribution("command", {
    "id": "restart_service",
    "label": "Restart Service",
    "action": "restart_service",
    "danger_level": "confirm",
    "input_schema": {
        "type": "object",
        "properties": {
            "service_name": {
                "type": "string",
                "minLength": 1,
                "pattern": "^[a-z][a-z0-9-]*$"
            },
            "force": {
                "type": "boolean",
                "default": False
            }
        },
        "required": ["service_name"],
    },
})
```

**Validation failure result:**
```json
{
  "status": "failed",
  "error": "Input validation failed at 'service_name': '' is too short"
}
```

## Handler Implementation

Command handlers are registered in the `CommandBus`. In V1, handlers are defined in `command_bus.py`.

### Basic Handler

```python
def my_handler(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the command.

    Args:
        args: Command arguments from the request
        context: Execution context (user_id, username, request_id, etc.)

    Returns:
        Result dictionary (will be returned to client)
    """
    return {
        "message": "Command executed successfully",
        "processed": args.get("input_value"),
        "executed_by": context.get("username"),
    }
```

### Async Handler

Handlers can be async:

```python
async def fetch_data_handler(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(args["url"]) as response:
            return {"data": await response.json()}
```

### Context Contents

The `context` dict contains:
- `user_id` - User's unique identifier
- `username` - User's display name
- `request_id` - Unique request identifier (for tracing)
- Any additional context from the request

### Timeout Handling

Commands have a default timeout of 30 seconds. Override per-command:

```python
ctx.register_contribution("command", {
    "id": "long_running",
    "label": "Long Running Task",
    "action": "long_task",
    "timeout_ms": 120000,  # 2 minutes
})
```

Timeout result:
```json
{
  "status": "timeout",
  "error": "Command execution timed out after 30000ms"
}
```

## Dry Run Support

Commands can support preview mode for safer operations:

```python
ctx.register_contribution("command", {
    "id": "clear_cache",
    "label": "Clear Cache",
    "action": "clear_cache",
    "danger_level": "danger",
    "dry_run_supported": True,
})
```

When executed with `dry_run: true`:
```json
{
  "status": "success",
  "dry_run_preview": {
    "would_execute": "clear_cache",
    "with_args": {"cache_type": "all"}
  }
}
```

## Execution Flow

1. **Request received** - Client sends command execution request
2. **Command lookup** - Find command definition by ID
3. **Authorization** - Check user capabilities against required_capabilities
4. **Input validation** - Validate args against input_schema (if defined)
5. **Confirmation check** - For confirm/danger levels, verify `confirmed: true`
6. **Dry run check** - If dry_run requested, return preview
7. **Handler dispatch** - Execute handler with timeout
8. **Audit logging** - Log result with redacted args
9. **Response** - Return result to client

## Complete Example

```python
# __init__.py
def register(ctx):
    # Read-only command
    ctx.register_contribution("command", {
        "id": "get_status",
        "label": "Get System Status",
        "icon": "activity",
        "shortcut": "Ctrl+Shift+I",
        "action": "get_status",
        "danger_level": "safe",
    })

    # Destructive command with full guardrails
    ctx.register_contribution("command", {
        "id": "reset_database",
        "label": "Reset Database",
        "icon": "database",
        "action": "reset_db",
        "danger_level": "danger",
        "required_capabilities": ["admin.database.reset"],
        "dry_run_supported": True,
        "audit_redaction": ["connection_string"],
        "input_schema": {
            "type": "object",
            "properties": {
                "database": {"type": "string", "enum": ["staging", "production"]},
                "connection_string": {"type": "string"},
                "confirm_name": {"type": "string"},
            },
            "required": ["database", "confirm_name"],
        },
        "timeout_ms": 60000,
    })
```

## API Reference

### Execute Command

```http
POST /api/commands/execute
Content-Type: application/json

{
  "command_id": "restart_service",
  "args": {
    "service_name": "api-gateway"
  },
  "confirmed": true,
  "dry_run": false
}
```

### Response

```json
{
  "command_id": "restart_service",
  "status": "success",
  "audit_id": "a1b2c3d4-...",
  "duration_ms": 1523.45,
  "danger_level": "confirm",
  "requires_confirmation": false,
  "result": {
    "message": "Service 'api-gateway' restart initiated",
    "service": "api-gateway",
    "status": "restarting"
  }
}
```

**Pending confirmation response** (when `confirmed: false` for confirm/danger commands):
```json
{
  "command_id": "restart_service",
  "status": "pending",
  "danger_level": "confirm",
  "requires_confirmation": true,
  "result": {
    "message": "This command requires confirmation (danger level: confirm)"
  }
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `success` | Command executed successfully |
| `failed` | Handler threw an exception |
| `denied` | User lacks required capabilities |
| `pending` | Awaiting confirmation (confirm/danger level) |
| `timeout` | Execution exceeded timeout_ms |
