"""
Registry builder - resolves contributions into slots with deterministic ordering.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any

from continuum.domain.regions import get_all_regions, get_region, Cardinality
from continuum.domain.themes import BUILTIN_THEMES, validate_theme


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
    themes: list[dict[str, Any]] = field(default_factory=list)
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
    plugin_themes: list[dict[str, Any]] = []

    for contrib in contributions:
        contrib_type = contrib.get("type")

        if contrib_type == "command":
            commands.append(contrib)
        elif contrib_type == "theme":
            plugin_themes.append(contrib)
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

    # Process themes: validate, resolve duplicates, merge with built-ins
    registry.themes = _resolve_themes(plugin_themes, report)

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

    # Include themes
    for theme in registry.themes:
        content_parts.append(f"theme:{theme.get('id', '')}:{theme.get('plugin_id', '')}")

    content = "|".join(content_parts)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _resolve_themes(
    plugin_themes: list[dict[str, Any]],
    report: RegistryBuildReport,
) -> list[dict[str, Any]]:
    """
    Resolve themes: validate, handle duplicates, merge with built-ins.

    Precedence for duplicate IDs (same rules as slot contributions):
    - Plugin themes override built-in themes with the same ID
    - Among plugins, higher priority wins; ties broken by discovery_index (lower wins)
    - Losers are logged as conflicts in the build report
    """
    resolved: list[dict[str, Any]] = []

    # Validate and collect valid plugin themes, keyed by ID
    valid_plugin_themes: dict[str, list[dict[str, Any]]] = {}
    for theme in plugin_themes:
        errors = validate_theme(theme)
        if errors:
            report.errors.extend(errors)
            continue
        theme_id = theme["id"]
        if theme_id not in valid_plugin_themes:
            valid_plugin_themes[theme_id] = []
        valid_plugin_themes[theme_id].append(theme)

    # Resolve duplicate plugin theme IDs using priority/discovery_index
    plugin_winners: dict[str, dict[str, Any]] = {}
    for theme_id, candidates in valid_plugin_themes.items():
        sorted_candidates = _sort_contributions(candidates)
        winner = sorted_candidates[0]
        plugin_winners[theme_id] = winner
        if len(sorted_candidates) > 1:
            losers = sorted_candidates[1:]
            conflict = Conflict(
                slot_id=f"theme:{theme_id}",
                winner=winner,
                losers=losers,
            )
            report.conflicts.append(conflict)
            report.warnings.append(
                f"Theme '{theme_id}' conflict: {winner.get('plugin_id')} "
                f"(priority={winner.get('priority', 100)}, index={winner.get('discovery_index')}) "
                f"wins over {len(losers)} other(s)"
            )

    # Merge: built-in themes first, plugin themes override by ID
    overridden_builtin_ids = set(plugin_winners.keys())
    for builtin in BUILTIN_THEMES:
        if builtin["id"] in overridden_builtin_ids:
            # Plugin overrides this built-in
            resolved.append(plugin_winners.pop(builtin["id"]))
        else:
            resolved.append(dict(builtin))

    # Append remaining plugin themes (non-overriding) sorted by priority
    remaining = _sort_contributions(list(plugin_winners.values()))
    resolved.extend(remaining)

    return resolved
