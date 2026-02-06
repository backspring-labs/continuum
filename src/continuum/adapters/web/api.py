"""
Continuum Web API - FastAPI routes.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from continuum.domain.lifecycle import LifecycleState
from continuum.domain.auth import UserContext
from continuum.domain.commands import CommandExecuteRequest


router = APIRouter()


def get_current_user() -> UserContext:
    """
    Get the current user context.

    In V1, this returns a mock operator with all capabilities.
    Future versions will integrate with auth middleware/JWT/etc.
    """
    return UserContext(
        user_id="operator",
        username="Operator",
        roles=("operator",),
        capabilities=("*",),  # V1: operators have all capabilities
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    lifecycle_state: str


class DiagnosticsResponse(BaseModel):
    """Diagnostics response."""

    lifecycle_state: str
    plugins: list[dict[str, Any]]
    warnings: list[str]
    errors: list[str]


class RegistryResponse(BaseModel):
    """Registry payload response."""

    lifecycle_state: str
    registry_fingerprint: str
    perspectives: list[dict[str, Any]]
    regions: dict[str, list[dict[str, Any]]]
    commands: list[dict[str, Any]]
    plugins: list[dict[str, Any]]
    diagnostics: dict[str, Any]


class CommandExecuteRequestBody(BaseModel):
    """Request body for command execution."""

    command_id: str = Field(..., description="The ID of the command to execute")
    args: dict[str, Any] = Field(default_factory=dict, description="Command arguments")
    dry_run: bool = Field(default=False, description="Preview without executing")
    confirmed: bool = Field(default=False, description="User confirmed dangerous action")


class CommandExecuteResponse(BaseModel):
    """Response from command execution."""

    command_id: str
    status: str
    audit_id: str
    duration_ms: float = 0.0
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    dry_run_preview: dict[str, Any] | None = None
    requires_confirmation: bool = False
    danger_level: str = "safe"


class AuditLogResponse(BaseModel):
    """Response containing audit log entries."""

    entries: list[dict[str, Any]]
    count: int


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Health check endpoint."""
    runtime = request.app.state.runtime
    state = runtime.lifecycle.state

    return HealthResponse(
        status="ok" if state == LifecycleState.READY else "degraded",
        lifecycle_state=state.value,
    )


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics(request: Request) -> DiagnosticsResponse:
    """Diagnostics endpoint."""
    runtime = request.app.state.runtime

    return DiagnosticsResponse(
        lifecycle_state=runtime.lifecycle.state.value,
        plugins=runtime.get_plugin_status(),
        warnings=runtime.get_warnings(),
        errors=runtime.get_errors(),
    )


@router.get("/api/registry", response_model=RegistryResponse)
async def registry(request: Request) -> RegistryResponse:
    """Registry payload endpoint."""
    runtime = request.app.state.runtime

    # Get regions and augment contributions with bundle_url
    regions = runtime.get_regions_with_bundle_urls()

    return RegistryResponse(
        lifecycle_state=runtime.lifecycle.state.value,
        registry_fingerprint=runtime.get_registry_fingerprint(),
        perspectives=runtime.get_perspectives(),
        regions=regions,
        commands=runtime.get_commands(),
        plugins=runtime.get_plugin_status(),
        diagnostics={
            "conflicts": runtime.get_conflicts(),
            "missing_required": runtime.get_missing_required(),
            "warnings": runtime.get_warnings(),
        },
    )


@router.get("/plugins/{plugin_id}/assets/{path:path}")
async def plugin_assets(plugin_id: str, path: str, request: Request) -> FileResponse:
    """
    Serve static assets from plugin dist directories.

    This enables dynamic loading of plugin UI bundles without compile-time
    coupling between the shell and plugins.
    """
    runtime = request.app.state.runtime
    plugins_dir = Path(runtime._plugins_dir)

    # Validate plugin_id format to prevent path traversal
    if ".." in plugin_id or "/" in plugin_id or "\\" in plugin_id:
        raise HTTPException(status_code=400, detail="Invalid plugin ID")

    # Validate path to prevent path traversal
    if ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Construct the asset path
    asset_path = plugins_dir / plugin_id / "dist" / path

    # Verify the path is within the expected directory
    try:
        asset_path = asset_path.resolve()
        expected_prefix = (plugins_dir / plugin_id / "dist").resolve()
        if not str(asset_path).startswith(str(expected_prefix)):
            raise HTTPException(status_code=403, detail="Access denied")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail=f"Asset not found: {path}")

    if not asset_path.is_file():
        raise HTTPException(status_code=404, detail=f"Not a file: {path}")

    # Determine content type based on extension
    content_type = "application/octet-stream"
    suffix = asset_path.suffix.lower()
    if suffix == ".js":
        content_type = "application/javascript"
    elif suffix == ".css":
        content_type = "text/css"
    elif suffix == ".json":
        content_type = "application/json"
    elif suffix == ".map":
        content_type = "application/json"

    return FileResponse(asset_path, media_type=content_type)


@router.post("/api/commands/execute", response_model=CommandExecuteResponse)
async def execute_command(
    body: CommandExecuteRequestBody,
    request: Request,
    user: UserContext = Depends(get_current_user),
) -> CommandExecuteResponse:
    """
    Execute a command.

    The command execution pipeline:
    1. Validates the command exists
    2. Checks authorization (deny-by-default)
    3. For CONFIRM/DANGER commands, requires confirmation flag
    4. Executes the handler
    5. Logs to audit trail

    Returns the execution result with audit_id for tracking.
    """
    runtime = request.app.state.runtime

    # Build the execution request
    exec_request = CommandExecuteRequest(
        command_id=body.command_id,
        args=body.args,
        dry_run=body.dry_run,
        confirmed=body.confirmed,
    )

    # Execute the command with the current user context
    result = await runtime.execute_command(exec_request, user)

    return CommandExecuteResponse(
        command_id=result.command_id,
        status=result.status.value,
        audit_id=result.audit_id,
        duration_ms=result.duration_ms,
        result=result.result,
        error=result.error,
        dry_run_preview=result.dry_run_preview,
        requires_confirmation=result.requires_confirmation,
        danger_level=result.danger_level,
    )


@router.get("/api/commands/audit", response_model=AuditLogResponse)
async def get_audit_log(request: Request, limit: int = 100) -> AuditLogResponse:
    """
    Get recent command execution audit log.

    Returns the most recent command executions with redacted sensitive arguments.
    """
    runtime = request.app.state.runtime
    entries = runtime.get_audit_log(limit=limit)

    return AuditLogResponse(
        entries=entries,
        count=len(entries),
    )
