"""
Perspective definitions for Continuum.

A Perspective is a curated work mode (e.g., Signal, Research, Time, Discovery, Systems).
"""

from dataclasses import dataclass
from enum import Enum


class PerspectiveId(Enum):
    """Built-in perspective identifiers."""

    SIGNAL = "signal"
    RESEARCH = "research"
    TIME = "time"
    DISCOVERY = "discovery"
    SYSTEMS = "systems"


@dataclass(frozen=True)
class PerspectiveSpec:
    """
    Specification for a perspective.

    Perspectives are curated work modes that organize the UI.
    """

    id: str
    label: str
    route_prefix: str
    description: str = ""


# Built-in perspectives
PERSPECTIVES: dict[str, PerspectiveSpec] = {
    PerspectiveId.SIGNAL.value: PerspectiveSpec(
        id=PerspectiveId.SIGNAL.value,
        label="Signal",
        route_prefix="/signal",
        description="Monitor signals, metrics, and alerts",
    ),
    PerspectiveId.RESEARCH.value: PerspectiveSpec(
        id=PerspectiveId.RESEARCH.value,
        label="Research",
        route_prefix="/research",
        description="Query and analyze data",
    ),
    PerspectiveId.TIME.value: PerspectiveSpec(
        id=PerspectiveId.TIME.value,
        label="Time",
        route_prefix="/time",
        description="Scheduling and timeline views",
    ),
    PerspectiveId.DISCOVERY.value: PerspectiveSpec(
        id=PerspectiveId.DISCOVERY.value,
        label="Discovery",
        route_prefix="/discovery",
        description="Browse and discover capabilities",
    ),
    PerspectiveId.SYSTEMS.value: PerspectiveSpec(
        id=PerspectiveId.SYSTEMS.value,
        label="Systems",
        route_prefix="/systems",
        description="System administration and diagnostics",
    ),
}


def get_perspective(perspective_id: str) -> PerspectiveSpec | None:
    """Get a perspective by ID."""
    return PERSPECTIVES.get(perspective_id)


def get_all_perspectives() -> list[PerspectiveSpec]:
    """Get all perspectives."""
    return list(PERSPECTIVES.values())
