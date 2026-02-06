"""
Command bus for Continuum.

The command bus handles command execution including:
- Command lookup and validation
- Input schema validation
- Authorization checks
- Handler dispatch with timeout
- Audit logging
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from continuum.domain.auth import PolicyDecision, PolicyEngine, UserContext
from continuum.domain.commands import (
    AuditEntry,
    CommandExecuteRequest,
    CommandExecuteResult,
    ExecutionStatus,
)
from continuum.domain.contributions import DangerLevel
from continuum.domain.events import get_event_bus


class CommandHandler(Protocol):
    """Protocol for command handlers."""

    def __call__(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute the command.

        Args:
            args: Command arguments
            context: Execution context (user info, request ID, etc.)

        Returns:
            Result dictionary
        """
        ...


# Default timeout for command execution (30 seconds)
DEFAULT_COMMAND_TIMEOUT_MS = 30000


@dataclass
class CommandDefinition:
    """Definition of a registered command."""

    id: str
    label: str
    handler: CommandHandler | None = None
    required_capabilities: list[str] = field(default_factory=list)
    danger_level: DangerLevel = DangerLevel.SAFE
    audit_redaction: list[str] = field(default_factory=list)
    dry_run_supported: bool = False
    client_side: bool = False  # If True, execution is handled by the UI
    input_schema: dict[str, Any] | None = None  # JSON Schema for args validation
    timeout_ms: int = DEFAULT_COMMAND_TIMEOUT_MS  # Execution timeout in milliseconds


class CommandBus:
    """
    Command execution bus.

    Handles command routing, authorization, execution, and audit logging.
    """

    def __init__(self) -> None:
        self._commands: dict[str, CommandDefinition] = {}
        self._handlers: dict[str, CommandHandler] = {}
        self._audit_log: list[AuditEntry] = []
        self._policy_engine = PolicyEngine()

        # Register built-in handlers
        self._register_builtin_handlers()

    def _register_builtin_handlers(self) -> None:
        """Register built-in command handlers."""

        # Sample action handler - demonstrates a simple command
        def sample_action_handler(
            args: dict[str, Any], context: dict[str, Any]
        ) -> dict[str, Any]:
            return {
                "message": "Sample action executed successfully!",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "args_received": args,
            }

        self._handlers["sample_action"] = sample_action_handler

        # Echo handler - useful for testing
        def echo_handler(
            args: dict[str, Any], context: dict[str, Any]
        ) -> dict[str, Any]:
            return {"echo": args, "context_keys": list(context.keys())}

        self._handlers["echo"] = echo_handler

        # Restart service handler (confirm level)
        def restart_service_handler(
            args: dict[str, Any], context: dict[str, Any]
        ) -> dict[str, Any]:
            service_name = args.get("service_name", "unknown")
            return {
                "message": f"Service '{service_name}' restart initiated",
                "service": service_name,
                "status": "restarting",
                "initiated_by": context.get("username", "unknown"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

        self._handlers["restart_service"] = restart_service_handler

        # Clear cache handler (danger level)
        def clear_cache_handler(
            args: dict[str, Any], context: dict[str, Any]
        ) -> dict[str, Any]:
            return {
                "message": "All caches cleared successfully",
                "caches_cleared": ["redis", "memcached", "local"],
                "initiated_by": context.get("username", "unknown"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

        self._handlers["clear_cache"] = clear_cache_handler

        # Update secret handler (with redaction)
        def update_secret_handler(
            args: dict[str, Any], context: dict[str, Any]
        ) -> dict[str, Any]:
            key = args.get("key", "unknown")
            return {
                "message": f"Secret '{key}' updated successfully",
                "key": key,
                "updated_by": context.get("username", "unknown"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

        self._handlers["update_secret"] = update_secret_handler

        # Deploy handler (requires capability)
        def deploy_handler(
            args: dict[str, Any], context: dict[str, Any]
        ) -> dict[str, Any]:
            return {
                "message": "Deployment initiated",
                "environment": "production",
                "initiated_by": context.get("username", "unknown"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

        self._handlers["deploy"] = deploy_handler

    def register_command(self, definition: CommandDefinition) -> None:
        """Register a command definition."""
        self._commands[definition.id] = definition

    def register_handler(self, command_id: str, handler: CommandHandler) -> None:
        """Register a handler for a command."""
        self._handlers[command_id] = handler

    def get_command(self, command_id: str) -> CommandDefinition | None:
        """Get a command definition by ID."""
        return self._commands.get(command_id)

    def load_commands_from_registry(
        self, commands: list[dict[str, Any]]
    ) -> None:
        """
        Load command definitions from the registry.

        Called by the runtime after registry resolution.
        """
        for cmd in commands:
            cmd_id = cmd.get("id", "")
            if not cmd_id:
                continue

            # Determine danger level
            danger_str = cmd.get("danger_level", "safe")
            try:
                danger_level = DangerLevel(danger_str)
            except ValueError:
                danger_level = DangerLevel.SAFE

            # Check if this is a client-side action
            action = cmd.get("action", "")
            client_side = action in ("open_command_palette", "toggle_drawer")

            definition = CommandDefinition(
                id=cmd_id,
                label=cmd.get("label", cmd_id),
                handler=self._handlers.get(action),
                required_capabilities=cmd.get("required_capabilities", []),
                danger_level=danger_level,
                audit_redaction=cmd.get("audit_redaction", []),
                dry_run_supported=cmd.get("dry_run_supported", False),
                client_side=client_side,
                input_schema=cmd.get("input_schema"),
                timeout_ms=cmd.get("timeout_ms", DEFAULT_COMMAND_TIMEOUT_MS),
            )

            self.register_command(definition)

    async def execute(
        self, request: CommandExecuteRequest, user: UserContext
    ) -> CommandExecuteResult:
        """
        Execute a command.

        Args:
            request: The execution request
            user: The user context

        Returns:
            CommandExecuteResult with status and result/error
        """
        start_time = time.perf_counter()

        # Look up command
        command = self.get_command(request.command_id)
        if command is None:
            return CommandExecuteResult(
                command_id=request.command_id,
                status=ExecutionStatus.FAILED,
                error=f"Unknown command: {request.command_id}",
            )

        # Check if client-side only
        if command.client_side:
            return CommandExecuteResult(
                command_id=request.command_id,
                status=ExecutionStatus.SUCCESS,
                result={"client_side": True, "action": request.command_id},
                danger_level=command.danger_level.value,
            )

        # Authorize
        policy_decision = self._policy_engine.evaluate(
            user, command.required_capabilities
        )

        if not policy_decision.is_allowed:
            duration_ms = (time.perf_counter() - start_time) * 1000
            audit_entry = self._log_audit(
                command=command,
                user=user,
                request=request,
                status=ExecutionStatus.DENIED,
                duration_ms=duration_ms,
                error=policy_decision.rationale,
            )
            return CommandExecuteResult(
                command_id=request.command_id,
                status=ExecutionStatus.DENIED,
                audit_id=audit_entry.audit_id,
                error=policy_decision.rationale,
                danger_level=command.danger_level.value,
            )

        # Validate input against schema
        if command.input_schema is not None:
            validation_error = self._validate_input(request.args, command.input_schema)
            if validation_error:
                duration_ms = (time.perf_counter() - start_time) * 1000
                audit_entry = self._log_audit(
                    command=command,
                    user=user,
                    request=request,
                    status=ExecutionStatus.FAILED,
                    duration_ms=duration_ms,
                    error=validation_error,
                )
                return CommandExecuteResult(
                    command_id=request.command_id,
                    status=ExecutionStatus.FAILED,
                    audit_id=audit_entry.audit_id,
                    error=validation_error,
                    danger_level=command.danger_level.value,
                )

        # Check confirmation for dangerous commands
        if command.danger_level in (DangerLevel.CONFIRM, DangerLevel.DANGER):
            if not request.confirmed:
                return CommandExecuteResult(
                    command_id=request.command_id,
                    status=ExecutionStatus.PENDING,
                    requires_confirmation=True,
                    danger_level=command.danger_level.value,
                    result={
                        "message": f"This command requires confirmation (danger level: {command.danger_level.value})",
                    },
                )

        # Handle dry run
        if request.dry_run:
            if not command.dry_run_supported:
                return CommandExecuteResult(
                    command_id=request.command_id,
                    status=ExecutionStatus.FAILED,
                    error="Dry run not supported for this command",
                    danger_level=command.danger_level.value,
                )
            # For dry run, return a preview without executing
            return CommandExecuteResult(
                command_id=request.command_id,
                status=ExecutionStatus.SUCCESS,
                dry_run_preview={
                    "would_execute": request.command_id,
                    "with_args": request.args,
                },
                danger_level=command.danger_level.value,
            )

        # Execute handler
        if command.handler is None:
            duration_ms = (time.perf_counter() - start_time) * 1000
            audit_entry = self._log_audit(
                command=command,
                user=user,
                request=request,
                status=ExecutionStatus.FAILED,
                duration_ms=duration_ms,
                error="No handler registered",
            )
            return CommandExecuteResult(
                command_id=request.command_id,
                status=ExecutionStatus.FAILED,
                audit_id=audit_entry.audit_id,
                error=f"No handler registered for command: {request.command_id}",
                danger_level=command.danger_level.value,
            )

        try:
            # Build execution context
            exec_context = {
                "user_id": user.user_id,
                "username": user.username,
                "request_id": request.context.get("request_id", ""),
                **request.context,
            }

            # Execute with timeout
            timeout_seconds = command.timeout_ms / 1000.0
            try:
                result = await asyncio.wait_for(
                    self._execute_handler(command.handler, request.args, exec_context),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Command execution timed out after {command.timeout_ms}ms"

                audit_entry = self._log_audit(
                    command=command,
                    user=user,
                    request=request,
                    status=ExecutionStatus.TIMEOUT,
                    duration_ms=duration_ms,
                    error=error_msg,
                )

                return CommandExecuteResult(
                    command_id=request.command_id,
                    status=ExecutionStatus.TIMEOUT,
                    audit_id=audit_entry.audit_id,
                    duration_ms=duration_ms,
                    error=error_msg,
                    danger_level=command.danger_level.value,
                )

            duration_ms = (time.perf_counter() - start_time) * 1000

            audit_entry = self._log_audit(
                command=command,
                user=user,
                request=request,
                status=ExecutionStatus.SUCCESS,
                duration_ms=duration_ms,
            )

            return CommandExecuteResult(
                command_id=request.command_id,
                status=ExecutionStatus.SUCCESS,
                audit_id=audit_entry.audit_id,
                duration_ms=duration_ms,
                result=result,
                danger_level=command.danger_level.value,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = str(e)

            audit_entry = self._log_audit(
                command=command,
                user=user,
                request=request,
                status=ExecutionStatus.FAILED,
                duration_ms=duration_ms,
                error=error_msg,
            )

            return CommandExecuteResult(
                command_id=request.command_id,
                status=ExecutionStatus.FAILED,
                audit_id=audit_entry.audit_id,
                duration_ms=duration_ms,
                error=error_msg,
                danger_level=command.danger_level.value,
            )

    def _validate_input(
        self, args: dict[str, Any], schema: dict[str, Any]
    ) -> str | None:
        """
        Validate command arguments against JSON Schema.

        Args:
            args: The command arguments to validate
            schema: JSON Schema to validate against

        Returns:
            Error message if validation fails, None if valid
        """
        try:
            jsonschema.validate(instance=args, schema=schema)
            return None
        except JsonSchemaValidationError as e:
            # Format a user-friendly error message
            path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            return f"Input validation failed at '{path}': {e.message}"

    async def _execute_handler(
        self,
        handler: CommandHandler,
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a command handler, supporting both sync and async handlers.

        Args:
            handler: The handler to execute
            args: Command arguments
            context: Execution context

        Returns:
            Handler result dictionary
        """
        # Run sync handlers in executor to not block event loop
        result = handler(args, context)
        # If handler returns a coroutine, await it
        if asyncio.iscoroutine(result):
            return await result
        return result

    def _log_audit(
        self,
        command: CommandDefinition,
        user: UserContext,
        request: CommandExecuteRequest,
        status: ExecutionStatus,
        duration_ms: float,
        error: str | None = None,
    ) -> AuditEntry:
        """Log an audit entry for a command execution."""
        entry = AuditEntry.create(
            command_id=command.id,
            user_id=user.user_id,
            status=status,
            duration_ms=duration_ms,
            args=request.args,
            redact_keys=command.audit_redaction,
            error=error,
            context={"request_id": request.context.get("request_id", "")},
        )
        self._audit_log.append(entry)

        # Keep only last 1000 entries in memory
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

        # Emit structured event
        get_event_bus().emit(
            "continuum.command.executed",
            {
                "audit_id": entry.audit_id,
                "command_id": command.id,
                "user_id": user.user_id,
                "status": status.value,
                "duration_ms": duration_ms,
                "danger_level": command.danger_level.value,
                "error": error,
            },
        )

        return entry

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent audit log entries."""
        entries = self._audit_log[-limit:]
        return [entry.to_dict() for entry in reversed(entries)]
