"""
Plugin manifest schema and validation.

Plugins are defined by a plugin.toml file with the following structure:

    [plugin]
    id = "vendor.plugin_name"
    name = "Display Name"
    version = "1.0.0"
    description = "Plugin description"
    required = false

    [plugin.ui]
    tag_prefix = "vendor-plugin-name"

    [[contributions.nav]]
    slot = "ui.slot.left_nav"
    perspective = "signal"
    label = "My Nav Item"
    icon = "chart"
    target = { type = "panel", panel_id = "my-panel" }
    priority = 100

    [[contributions.panel]]
    slot = "ui.slot.main"
    perspective = "signal"
    component = "main-panel"
    priority = 100
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator


class NavTargetManifest(BaseModel):
    """Navigation target in manifest."""

    type: str = Field(..., pattern="^(panel|drawer|command|route)$")
    panel_id: str | None = None
    drawer_id: str | None = None
    command_id: str | None = None
    route: str | None = None


class NavContributionManifest(BaseModel):
    """Nav contribution in manifest."""

    slot: str = "ui.slot.left_nav"
    perspective: str | None = None
    label: str
    icon: str | None = None
    target: NavTargetManifest
    priority: int = 100


class PanelContributionManifest(BaseModel):
    """Panel contribution in manifest."""

    slot: str
    perspective: str | None = None
    component: str
    priority: int = 100


class DrawerContributionManifest(BaseModel):
    """Drawer contribution in manifest."""

    id: str
    component: str
    title: str | None = None
    width: str = "400px"


class CommandContributionManifest(BaseModel):
    """Command contribution in manifest."""

    id: str
    label: str
    icon: str | None = None
    shortcut: str | None = None
    action: str  # JavaScript action identifier


class DiagnosticContributionManifest(BaseModel):
    """Diagnostic contribution in manifest."""

    id: str
    label: str
    check: str  # Health check endpoint or function


class ContributionsManifest(BaseModel):
    """All contributions from a plugin."""

    nav: list[NavContributionManifest] = Field(default_factory=list)
    panel: list[PanelContributionManifest] = Field(default_factory=list)
    drawer: list[DrawerContributionManifest] = Field(default_factory=list)
    command: list[CommandContributionManifest] = Field(default_factory=list)
    diagnostic: list[DiagnosticContributionManifest] = Field(default_factory=list)


class PluginUIManifest(BaseModel):
    """UI configuration for a plugin."""

    tag_prefix: str = Field(..., pattern="^[a-z][a-z0-9-]*$")


class PluginMetaManifest(BaseModel):
    """Plugin metadata section."""

    id: str = Field(..., pattern="^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$")
    name: str
    version: str = Field(..., pattern="^\\d+\\.\\d+\\.\\d+")
    description: str = ""
    required: bool = False
    ui: PluginUIManifest

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate plugin ID is vendor.plugin_name format."""
        if "." not in v:
            raise ValueError("Plugin ID must be in vendor.plugin_name format")
        return v


class PluginManifest(BaseModel):
    """Complete plugin manifest (plugin.toml)."""

    plugin: PluginMetaManifest
    contributions: ContributionsManifest = Field(default_factory=ContributionsManifest)


@dataclass
class ManifestValidationResult:
    """Result of manifest validation."""

    valid: bool
    manifest: PluginManifest | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_manifest(data: dict[str, Any]) -> ManifestValidationResult:
    """
    Validate a plugin manifest dictionary.

    Args:
        data: Parsed TOML data from plugin.toml

    Returns:
        ManifestValidationResult with validation status and parsed manifest
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        manifest = PluginManifest.model_validate(data)

        # Additional validation: tag_prefix should derive from plugin ID
        expected_prefix = manifest.plugin.id.replace(".", "-").replace("_", "-")
        if manifest.plugin.ui.tag_prefix != expected_prefix:
            warnings.append(
                f"tag_prefix '{manifest.plugin.ui.tag_prefix}' does not match "
                f"expected '{expected_prefix}' derived from plugin ID"
            )

        # Validate contribution slot references
        valid_slots = {
            "ui.slot.left_nav",
            "ui.slot.header",
            "ui.slot.main",
            "ui.slot.right_rail",
            "ui.slot.footer",
            "ui.slot.modal",
            "ui.slot.drawer",
            "ui.slot.toast_stack",
        }

        for nav in manifest.contributions.nav:
            if nav.slot not in valid_slots:
                errors.append(f"Invalid nav slot: {nav.slot}")

        for panel in manifest.contributions.panel:
            if panel.slot not in valid_slots:
                errors.append(f"Invalid panel slot: {panel.slot}")

        # Validate perspective references
        valid_perspectives = {"signal", "research", "time", "discovery", "systems"}

        for nav in manifest.contributions.nav:
            if nav.perspective and nav.perspective not in valid_perspectives:
                warnings.append(f"Unknown perspective in nav: {nav.perspective}")

        for panel in manifest.contributions.panel:
            if panel.perspective and panel.perspective not in valid_perspectives:
                warnings.append(f"Unknown perspective in panel: {panel.perspective}")

        if errors:
            return ManifestValidationResult(valid=False, errors=errors, warnings=warnings)

        return ManifestValidationResult(
            valid=True, manifest=manifest, errors=[], warnings=warnings
        )

    except Exception as e:
        return ManifestValidationResult(valid=False, errors=[str(e)])


def load_manifest_from_toml(toml_path: str) -> ManifestValidationResult:
    """
    Load and validate a plugin manifest from a TOML file.

    Args:
        toml_path: Path to plugin.toml file

    Returns:
        ManifestValidationResult with validation status and parsed manifest
    """
    try:
        import tomli

        with open(toml_path, "rb") as f:
            data = tomli.load(f)

        return validate_manifest(data)

    except FileNotFoundError:
        return ManifestValidationResult(valid=False, errors=[f"File not found: {toml_path}"])
    except Exception as e:
        return ManifestValidationResult(valid=False, errors=[f"Failed to parse TOML: {e}"])
