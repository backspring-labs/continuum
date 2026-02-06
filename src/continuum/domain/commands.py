"""
Command execution models for Continuum.

These models define the request/response contract for command execution,
as well as audit logging structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class ExecutionStatus(Enum):
    """Status of a command execution."""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    DENIED = "denied"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class CommandExecuteRequest:
    """
    Request to execute a command.

    Attributes:
        command_id: The ID of the command to execute
        args: Arguments to pass to the command handler
        dry_run: If True, preview the command without executing
        confirmed: If True, user has confirmed a CONFIRM/DANGER level command
        context: Additional context (user info added by the system)
    """

    command_id: str
    args: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    confirmed: bool = False
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Generate request ID if not provided in context
        if "request_id" not in self.context:
            self.context["request_id"] = str(uuid.uuid4())


@dataclass
class CommandExecuteResult:
    """
    Result of a command execution.

    Attributes:
        command_id: The ID of the executed command
        status: The execution status
        audit_id: Unique ID for audit trail
        duration_ms: Execution duration in milliseconds
        result: Command result data (if success)
        error: Error message (if failed)
        dry_run_preview: Preview data (if dry_run was True)
        requires_confirmation: True if command needs user confirmation
        danger_level: The command's danger level (for UI)
    """

    command_id: str
    status: ExecutionStatus
    audit_id: str = ""
    duration_ms: float = 0.0
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    dry_run_preview: dict[str, Any] | None = None
    requires_confirmation: bool = False
    danger_level: str = "safe"

    def __post_init__(self) -> None:
        if not self.audit_id:
            self.audit_id = str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "command_id": self.command_id,
            "status": self.status.value,
            "audit_id": self.audit_id,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "error": self.error,
            "dry_run_preview": self.dry_run_preview,
            "requires_confirmation": self.requires_confirmation,
            "danger_level": self.danger_level,
        }


@dataclass
class AuditEntry:
    """
    Audit log entry for command execution.

    Sensitive arguments are redacted based on the command's audit_redaction list.
    """

    audit_id: str
    command_id: str
    user_id: str
    timestamp: datetime
    status: ExecutionStatus
    duration_ms: float
    args_redacted: dict[str, Any]  # Sensitive values replaced with "[REDACTED]"
    error: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        command_id: str,
        user_id: str,
        status: ExecutionStatus,
        duration_ms: float,
        args: dict[str, Any],
        redact_keys: list[str],
        error: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> "AuditEntry":
        """Create an audit entry with redacted arguments."""
        # Redact sensitive arguments
        args_redacted = {}
        for key, value in args.items():
            if key in redact_keys:
                args_redacted[key] = "[REDACTED]"
            else:
                args_redacted[key] = value

        return cls(
            audit_id=str(uuid.uuid4()),
            command_id=command_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            status=status,
            duration_ms=duration_ms,
            args_redacted=args_redacted,
            error=error,
            context=context or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "audit_id": self.audit_id,
            "command_id": self.command_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "args_redacted": self.args_redacted,
            "error": self.error,
            "context": self.context,
        }
