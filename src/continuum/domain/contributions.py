"""
Contribution type definitions for Continuum.

Plugins contribute UI panels, navigation items, commands, etc.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DangerLevel(Enum):
    """Command danger level for UI guardrails."""

    SAFE = "safe"
    CONFIRM = "confirm"
    DANGER = "danger"


class NavTargetType(Enum):
    """Navigation target types."""

    PERSPECTIVE = "perspective"
    ROUTE = "route"
    ACTION = "action"


@dataclass(frozen=True)
class NavTarget:
    """Navigation target specification."""

    type: NavTargetType
    value: str  # perspective_id, route path, or action_id


@dataclass(frozen=True)
class PanelContribution:
    """
    A panel contribution to a region slot.

    Panels are the primary UI building blocks.
    """

    id: str
    slot_id: str
    component: str  # Full Web Component tag name
    props: dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    perspective_scope: str | None = None  # If set, only render in this perspective
    required: bool = False


@dataclass(frozen=True)
class NavContribution:
    """
    A navigation item contribution.

    Nav items appear in the left nav and trigger perspective switches,
    routes, or actions.
    """

    id: str
    group: str
    label: str
    icon: str
    target: NavTarget
    priority: int = 100
    required: bool = False
    # Note: NavContribution does NOT have perspective_scope in V1


@dataclass(frozen=True)
class DrawerContribution:
    """
    A drawer (slide-in panel) contribution.

    Drawers slide in from the right edge when triggered.
    """

    id: str
    slot_id: str  # Should be ui.slot.drawer
    component: str  # Full Web Component tag name
    props: dict[str, Any] = field(default_factory=dict)
    trigger_action_id: str = ""
    required: bool = False


@dataclass(frozen=True)
class CommandContribution:
    """
    A command contribution.

    Commands are operator actions that can be executed via the command palette.
    """

    id: str
    label: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    handler: str = ""  # Handler reference
    danger_level: DangerLevel = DangerLevel.SAFE
    audit_redaction: list[str] = field(default_factory=list)
    idempotency_hint: str | None = None
    dry_run_supported: bool = False


@dataclass(frozen=True)
class DiagnosticContribution:
    """
    A diagnostic contribution.

    Diagnostics provide health checks and version info for the Systems perspective.
    """

    id: str
    health_check: str = ""  # Health check function reference
    version_info: dict[str, str] = field(default_factory=dict)
