"""
Continuum Web API - FastAPI routes.
"""

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from continuum.domain.lifecycle import LifecycleState


router = APIRouter()


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

    return RegistryResponse(
        lifecycle_state=runtime.lifecycle.state.value,
        registry_fingerprint=runtime.get_registry_fingerprint(),
        perspectives=runtime.get_perspectives(),
        regions=runtime.get_regions(),
        commands=runtime.get_commands(),
        plugins=runtime.get_plugin_status(),
        diagnostics={
            "conflicts": runtime.get_conflicts(),
            "missing_required": runtime.get_missing_required(),
            "warnings": runtime.get_warnings(),
        },
    )
