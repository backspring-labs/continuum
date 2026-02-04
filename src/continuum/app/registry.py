"""
Registry builder - resolves contributions into slots with deterministic ordering.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any

from continuum.domain.regions import get_all_regions, get_region, Cardinality


@dataclass
class Conflict:
    """A conflict between contributions for a ONE-cardinality slot."""

    slot_id: str
    winner: dict[str, Any]
    losers: list[dict[str, Any]]


@dataclass
class RegistryBuildReport:
    """Report from building the registry."""

    slot_counts: dict[str, int] = field(default_factory=dict)
    conflicts: list[Conflict] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ResolvedRegistry:
    """The resolved contribution registry."""

    slots: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    commands: list[dict[str, Any]] = field(default_factory=list)
    fingerprint: str = ""
    report: RegistryBuildReport = field(default_factory=RegistryBuildReport)


def _sort_contributions(contributions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort contributions by priority (descending), then discovery_index (ascending).

    This provides deterministic ordering:
    - Higher priority wins
    - For equal priority, earlier discovered plugin wins
    """
    return sorted(
        contributions,
        key=lambda c: (-c.get("priority", 100), c.get("discovery_index", 0)),
    )


def build_registry(contributions: list[dict[str, Any]]) -> ResolvedRegistry:
    """
    Build the resolved registry from a list of contributions.

    Applies ordering rules and cardinality enforcement.

    Args:
        contributions: List of contribution dicts from loaded plugins

    Returns:
        ResolvedRegistry with resolved slots and build report
    """
    registry = ResolvedRegistry()
    report = registry.report

    # Initialize all slots
    for region in get_all_regions():
        registry.slots[region.slot_id] = []

    # Group contributions by type and slot
    slot_contributions: dict[str, list[dict[str, Any]]] = {}
    commands: list[dict[str, Any]] = []

    for contrib in contributions:
        contrib_type = contrib.get("type")

        if contrib_type == "command":
            commands.append(contrib)
        elif contrib_type in ("nav", "panel", "drawer", "diagnostic"):
            slot_id = contrib.get("slot")
            if slot_id:
                if slot_id not in slot_contributions:
                    slot_contributions[slot_id] = []
                slot_contributions[slot_id].append(contrib)

    # Process each slot
    for slot_id, contribs in slot_contributions.items():
        region = get_region(slot_id)

        # Sort contributions
        sorted_contribs = _sort_contributions(contribs)

        if region is None:
            # Unknown slot - add warning
            report.warnings.append(f"Unknown slot '{slot_id}' referenced by contributions")
            continue

        if region.cardinality == Cardinality.ONE:
            # ONE cardinality: take first (highest priority), log conflicts
            if sorted_contribs:
                winner = sorted_contribs[0]
                registry.slots[slot_id] = [winner]
                report.slot_counts[slot_id] = 1

                if len(sorted_contribs) > 1:
                    # Log conflict
                    losers = sorted_contribs[1:]
                    conflict = Conflict(slot_id=slot_id, winner=winner, losers=losers)
                    report.conflicts.append(conflict)
                    report.warnings.append(
                        f"Slot '{slot_id}' conflict: {winner.get('plugin_id')} "
                        f"(priority={winner.get('priority', 100)}, index={winner.get('discovery_index')}) "
                        f"wins over {len(losers)} other(s)"
                    )
        else:
            # MANY cardinality: include all, ordered
            registry.slots[slot_id] = sorted_contribs
            report.slot_counts[slot_id] = len(sorted_contribs)

    # Process commands
    registry.commands = _sort_contributions(commands)

    # Check for missing required slots
    for region in get_all_regions():
        if region.required and not registry.slots.get(region.slot_id):
            report.missing_required.append(region.slot_id)
            report.errors.append(f"Required slot '{region.slot_id}' has no contributions")

    # Calculate fingerprint
    registry.fingerprint = _calculate_fingerprint(registry)

    return registry


def _calculate_fingerprint(registry: ResolvedRegistry) -> str:
    """
    Calculate a deterministic fingerprint for the registry state.

    The fingerprint changes when:
    - Contributions change
    - Ordering changes
    - Commands change
    """
    content_parts = []

    # Include sorted slot contents
    for slot_id in sorted(registry.slots.keys()):
        slot_contribs = registry.slots[slot_id]
        for contrib in slot_contribs:
            content_parts.append(
                f"{slot_id}:{contrib.get('plugin_id')}:{contrib.get('priority', 100)}"
            )

    # Include commands
    for cmd in registry.commands:
        content_parts.append(f"cmd:{cmd.get('id', '')}:{cmd.get('plugin_id', '')}")

    content = "|".join(content_parts)
    return hashlib.sha256(content.encode()).hexdigest()[:16]
