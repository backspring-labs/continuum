"""
Plugin loader - imports plugin modules and registers contributions.
"""

import importlib.util
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from continuum.app.discovery import DiscoveredPlugin


@dataclass
class LoadedPlugin:
    """A loaded plugin with its module and contributions."""

    plugin_id: str
    discovery_index: int
    module: Any | None = None
    load_time_ms: float = 0.0
    status: str = "LOADED"  # LOADED, FAILED
    error: str | None = None
    contributions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LoadResult:
    """Result of plugin loading."""

    plugins: list[LoadedPlugin] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PluginContext:
    """Context passed to plugin registration functions."""

    def __init__(self, plugin_id: str, discovery_index: int) -> None:
        self.plugin_id = plugin_id
        self.discovery_index = discovery_index
        self._contributions: list[dict[str, Any]] = []

    def register_contribution(self, contribution_type: str, data: dict[str, Any]) -> None:
        """Register a contribution from this plugin."""
        contribution = {
            "type": contribution_type,
            "plugin_id": self.plugin_id,
            "discovery_index": self.discovery_index,
            **data,
        }
        self._contributions.append(contribution)

    def get_contributions(self) -> list[dict[str, Any]]:
        """Get all registered contributions."""
        return self._contributions.copy()


def load_plugins(
    discovered: list[DiscoveredPlugin],
    on_load: Callable[[LoadedPlugin], None] | None = None,
) -> LoadResult:
    """
    Load discovered plugins by importing their entrypoints.

    Loads in discovery order (deterministic).

    Args:
        discovered: List of discovered plugins to load
        on_load: Optional callback invoked after each plugin loads

    Returns:
        LoadResult with loaded plugins, errors, and warnings
    """
    result = LoadResult()

    for plugin in discovered:
        start_time = time.perf_counter()

        loaded = LoadedPlugin(
            plugin_id=plugin.plugin_id,
            discovery_index=plugin.discovery_index,
        )

        # Check if this is a required plugin
        is_required = plugin.manifest.plugin.required

        def record_failure(error_msg: str) -> None:
            """Record a plugin failure as error (required) or warning (optional)."""
            loaded.status = "FAILED"
            loaded.error = error_msg
            msg = f"Plugin {plugin.plugin_id}: {error_msg}"
            if is_required:
                result.errors.append(msg)
            else:
                result.warnings.append(msg)

        try:
            # Look for __init__.py in plugin directory
            init_path = plugin.directory / "__init__.py"

            if not init_path.exists():
                record_failure(f"No __init__.py found in {plugin.directory}")
                result.plugins.append(loaded)
                continue

            # Import the plugin module
            module_name = f"continuum_plugin_{plugin.plugin_id.replace('.', '_')}"

            spec = importlib.util.spec_from_file_location(module_name, init_path)
            if spec is None or spec.loader is None:
                record_failure(f"Could not create module spec for {init_path}")
                result.plugins.append(loaded)
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            loaded.module = module

            # Create context for contribution registration
            ctx = PluginContext(plugin.plugin_id, plugin.discovery_index)

            # Call register function if it exists
            if hasattr(module, "register"):
                register_func = getattr(module, "register")
                register_func(ctx)
                loaded.contributions = ctx.get_contributions()

            loaded.status = "LOADED"

        except Exception as e:
            record_failure(str(e))

        finally:
            loaded.load_time_ms = (time.perf_counter() - start_time) * 1000
            result.plugins.append(loaded)

            if on_load:
                on_load(loaded)

    return result
