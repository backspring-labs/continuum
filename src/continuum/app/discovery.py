"""
Plugin discovery - scans plugin directories and validates manifests.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from continuum.domain.manifest import (
    PluginManifest,
    ManifestValidationResult,
    load_manifest_from_toml,
)


@dataclass
class DiscoveredPlugin:
    """A discovered plugin with its manifest and metadata."""

    plugin_id: str
    directory: Path
    manifest: PluginManifest
    discovery_index: int
    status: str = "DISCOVERED"  # DISCOVERED, LOADING, LOADED, FAILED, DISABLED
    error: str | None = None


@dataclass
class DiscoveryResult:
    """Result of plugin discovery."""

    plugins: list[DiscoveredPlugin] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def discover_plugins(plugins_dir: str = "./plugins") -> DiscoveryResult:
    """
    Discover plugins in the specified directory.

    Scans for plugin directories containing plugin.toml manifests.
    Discovery order is deterministic: alphabetical by directory name.

    Args:
        plugins_dir: Path to plugins directory (default: ./plugins)

    Returns:
        DiscoveryResult with discovered plugins, errors, and warnings
    """
    result = DiscoveryResult()
    plugins_path = Path(plugins_dir)

    # Check if plugins directory exists
    if not plugins_path.exists():
        result.warnings.append(f"Plugins directory not found: {plugins_dir}")
        return result

    if not plugins_path.is_dir():
        result.errors.append(f"Plugins path is not a directory: {plugins_dir}")
        return result

    # Get all subdirectories, sorted alphabetically for deterministic order
    plugin_dirs = sorted(
        [d for d in plugins_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )

    discovery_index = 0
    for plugin_dir in plugin_dirs:
        manifest_path = plugin_dir / "plugin.toml"

        if not manifest_path.exists():
            result.warnings.append(f"No plugin.toml in {plugin_dir.name}, skipping")
            continue

        # Load and validate manifest
        validation = load_manifest_from_toml(str(manifest_path))

        if not validation.valid:
            result.errors.append(
                f"Invalid manifest in {plugin_dir.name}: {'; '.join(validation.errors)}"
            )
            continue

        manifest = validation.manifest
        assert manifest is not None  # validated above

        # Validate directory name matches plugin ID
        expected_dir_name = manifest.plugin.id
        if plugin_dir.name != expected_dir_name:
            result.errors.append(
                f"Directory name '{plugin_dir.name}' does not match plugin ID "
                f"'{expected_dir_name}' in manifest"
            )
            continue

        # Add any validation warnings
        result.warnings.extend(validation.warnings)

        # Create discovered plugin entry
        discovered = DiscoveredPlugin(
            plugin_id=manifest.plugin.id,
            directory=plugin_dir,
            manifest=manifest,
            discovery_index=discovery_index,
        )
        result.plugins.append(discovered)
        discovery_index += 1

    return result
