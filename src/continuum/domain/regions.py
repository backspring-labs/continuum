"""
Region (Slot) definitions for Continuum.

Regions are UI anchors where plugins contribute panels.
"""

from dataclasses import dataclass
from enum import Enum


class Cardinality(Enum):
    """Slot cardinality - how many contributions are allowed."""

    ONE = "one"
    MANY = "many"


class SlotId(Enum):
    """Built-in slot identifiers."""

    LEFT_NAV = "ui.slot.left_nav"
    HEADER = "ui.slot.header"
    MAIN = "ui.slot.main"
    RIGHT_RAIL = "ui.slot.right_rail"
    FOOTER = "ui.slot.footer"
    MODAL = "ui.slot.modal"
    DRAWER = "ui.slot.drawer"
    TOAST_STACK = "ui.slot.toast_stack"


@dataclass(frozen=True)
class RegionSpec:
    """
    Specification for a region (slot).

    Regions are fixed layout anchors that accept plugin contributions.
    """

    slot_id: str
    cardinality: Cardinality
    required: bool
    description: str = ""


# Built-in regions (single source of truth)
REGIONS: dict[str, RegionSpec] = {
    SlotId.LEFT_NAV.value: RegionSpec(
        slot_id=SlotId.LEFT_NAV.value,
        cardinality=Cardinality.MANY,
        required=False,
        description="Perspective switcher + action triggers",
    ),
    SlotId.HEADER.value: RegionSpec(
        slot_id=SlotId.HEADER.value,
        cardinality=Cardinality.ONE,
        required=False,
        description="Title, search, user profile",
    ),
    SlotId.MAIN.value: RegionSpec(
        slot_id=SlotId.MAIN.value,
        cardinality=Cardinality.MANY,
        required=False,
        description="Primary content area, perspective-scoped panel assembly",
    ),
    SlotId.RIGHT_RAIL.value: RegionSpec(
        slot_id=SlotId.RIGHT_RAIL.value,
        cardinality=Cardinality.MANY,
        required=False,
        description="Secondary panels (activity feeds, lists)",
    ),
    SlotId.FOOTER.value: RegionSpec(
        slot_id=SlotId.FOOTER.value,
        cardinality=Cardinality.ONE,
        required=False,
        description="Status bar, system info",
    ),
    SlotId.MODAL.value: RegionSpec(
        slot_id=SlotId.MODAL.value,
        cardinality=Cardinality.MANY,
        required=False,
        description="Overlay dialogs (command palette, confirmations)",
    ),
    SlotId.DRAWER.value: RegionSpec(
        slot_id=SlotId.DRAWER.value,
        cardinality=Cardinality.MANY,
        required=False,
        description="Slide-in panels (agent chat, detail views)",
    ),
    SlotId.TOAST_STACK.value: RegionSpec(
        slot_id=SlotId.TOAST_STACK.value,
        cardinality=Cardinality.MANY,
        required=False,
        description="Transient notifications, stacked bottom-right",
    ),
}


def get_region(slot_id: str) -> RegionSpec | None:
    """Get a region by slot ID."""
    return REGIONS.get(slot_id)


def get_all_regions() -> list[RegionSpec]:
    """Get all regions."""
    return list(REGIONS.values())


def is_required_slot(slot_id: str) -> bool:
    """Check if a slot is required."""
    region = REGIONS.get(slot_id)
    return region.required if region else False
