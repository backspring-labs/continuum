"""
Continuum domain models.
"""

from continuum.domain.lifecycle import LifecycleManager, LifecycleState, LifecycleEvent
from continuum.domain.perspectives import PerspectiveSpec, get_all_perspectives, get_perspective
from continuum.domain.regions import RegionSpec, Cardinality, get_all_regions, get_region
from continuum.domain.contributions import (
    PanelContribution,
    NavContribution,
    DrawerContribution,
    CommandContribution,
    DiagnosticContribution,
    DangerLevel,
    NavTarget,
    NavTargetType,
)
from continuum.domain.manifest import (
    PluginManifest,
    ManifestValidationResult,
    validate_manifest,
    load_manifest_from_toml,
)

__all__ = [
    "LifecycleManager",
    "LifecycleState",
    "LifecycleEvent",
    "PerspectiveSpec",
    "get_all_perspectives",
    "get_perspective",
    "RegionSpec",
    "Cardinality",
    "get_all_regions",
    "get_region",
    "PanelContribution",
    "NavContribution",
    "DrawerContribution",
    "CommandContribution",
    "DiagnosticContribution",
    "DangerLevel",
    "NavTarget",
    "NavTargetType",
    "PluginManifest",
    "ManifestValidationResult",
    "validate_manifest",
    "load_manifest_from_toml",
]
