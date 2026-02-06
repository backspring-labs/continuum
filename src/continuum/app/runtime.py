"""
Continuum Runtime - orchestrates lifecycle, plugins, and registry.
"""

from dataclasses import dataclass, field
from typing import Any

from continuum.domain.lifecycle import LifecycleManager, LifecycleState
from continuum.domain.perspectives import get_all_perspectives, PerspectiveSpec
from continuum.domain.regions import get_all_regions, RegionSpec
from continuum.domain.auth import UserContext
from continuum.domain.commands import CommandExecuteRequest, CommandExecuteResult
from continuum.app.discovery import discover_plugins, DiscoveredPlugin
from continuum.app.loader import load_plugins, LoadedPlugin
from continuum.app.registry import build_registry, ResolvedRegistry
from continuum.app.command_bus import CommandBus


@dataclass
class PluginStatus:
    """Status of a loaded plugin."""

    id: str
    name: str
    version: str
    status: str  # DISCOVERED, LOADING, LOADED, FAILED, DISABLED
    discovery_index: int
    required: bool
    error: str | None = None
    contribution_count: int = 0
    load_time_ms: float = 0.0


@dataclass
class RegistryState:
    """Resolved registry state."""

    perspectives: list[PerspectiveSpec] = field(default_factory=list)
    regions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    commands: list[dict[str, Any]] = field(default_factory=list)
    plugins: list[PluginStatus] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fingerprint: str = ""


class ContinuumRuntime:
    """
    Main runtime for Continuum.

    Manages lifecycle, plugin discovery/loading, and registry resolution.
    """

    def __init__(self, plugins_dir: str = "./plugins") -> None:
        self.lifecycle = LifecycleManager()
        self._registry = RegistryState()
        self._plugins_dir = plugins_dir
        self._discovered_plugins: list[DiscoveredPlugin] = []
        self._loaded_plugins: list[LoadedPlugin] = []
        self._resolved_registry: ResolvedRegistry | None = None
        self._command_bus = CommandBus()

    async def boot(self) -> None:
        """
        Boot the runtime through all lifecycle stages.

        Transitions: BOOTING -> DISCOVERING -> LOADING -> RESOLVING -> READY/DEGRADED
        """
        try:
            # Discover plugins
            self.lifecycle.transition_to(LifecycleState.DISCOVERING_PLUGINS)
            await self._discover_plugins()

            # Load plugins
            self.lifecycle.transition_to(LifecycleState.LOADING_PLUGINS)
            await self._load_plugins()

            # Resolve registry
            self.lifecycle.transition_to(LifecycleState.RESOLVING_REGISTRY)
            await self._resolve_registry()

            # Check for degraded state
            if self._should_degrade():
                self.lifecycle.transition_to(
                    LifecycleState.DEGRADED,
                    {"reason": "Required plugins or slots missing"},
                )
            else:
                self.lifecycle.transition_to(LifecycleState.READY)

        except Exception as e:
            self._registry.errors.append(str(e))
            if self.lifecycle.state != LifecycleState.DEGRADED:
                # Try to transition to DEGRADED if possible
                try:
                    # Skip to RESOLVING_REGISTRY if needed
                    while self.lifecycle.state not in (
                        LifecycleState.RESOLVING_REGISTRY,
                        LifecycleState.READY,
                        LifecycleState.DEGRADED,
                    ):
                        next_states = {
                            LifecycleState.BOOTING: LifecycleState.DISCOVERING_PLUGINS,
                            LifecycleState.DISCOVERING_PLUGINS: LifecycleState.LOADING_PLUGINS,
                            LifecycleState.LOADING_PLUGINS: LifecycleState.RESOLVING_REGISTRY,
                        }
                        if self.lifecycle.state in next_states:
                            self.lifecycle.transition_to(next_states[self.lifecycle.state])

                    if self.lifecycle.state == LifecycleState.RESOLVING_REGISTRY:
                        self.lifecycle.transition_to(
                            LifecycleState.DEGRADED,
                            {"reason": str(e)},
                        )
                except ValueError:
                    pass  # Can't transition, stay in current state

    async def shutdown(self) -> None:
        """Shutdown the runtime."""
        if self.lifecycle.state in (LifecycleState.READY, LifecycleState.DEGRADED):
            self.lifecycle.transition_to(LifecycleState.STOPPING)
            self.lifecycle.transition_to(LifecycleState.STOPPED)

    async def _discover_plugins(self) -> None:
        """Discover plugins in the plugins directory."""
        self._registry.perspectives = get_all_perspectives()

        # Initialize regions with empty contribution lists
        for region in get_all_regions():
            self._registry.regions[region.slot_id] = []

        # Discover plugins
        discovery_result = discover_plugins(self._plugins_dir)
        self._discovered_plugins = discovery_result.plugins
        self._registry.warnings.extend(discovery_result.warnings)
        self._registry.errors.extend(discovery_result.errors)

    async def _load_plugins(self) -> None:
        """Load discovered plugins."""
        if not self._discovered_plugins:
            return

        load_result = load_plugins(self._discovered_plugins)
        self._loaded_plugins = load_result.plugins
        self._registry.warnings.extend(load_result.warnings)
        self._registry.errors.extend(load_result.errors)

        # Update plugin status list
        for loaded in self._loaded_plugins:
            # Find the discovered plugin to get manifest info
            discovered = next(
                (p for p in self._discovered_plugins if p.plugin_id == loaded.plugin_id),
                None,
            )
            if discovered:
                status = PluginStatus(
                    id=loaded.plugin_id,
                    name=discovered.manifest.plugin.name,
                    version=discovered.manifest.plugin.version,
                    status=loaded.status,
                    discovery_index=loaded.discovery_index,
                    required=discovered.manifest.plugin.required,
                    error=loaded.error,
                    contribution_count=len(loaded.contributions),
                    load_time_ms=loaded.load_time_ms,
                )
                self._registry.plugins.append(status)

    async def _resolve_registry(self) -> None:
        """Resolve the contribution registry."""
        # Collect all contributions from loaded plugins
        all_contributions: list[dict[str, Any]] = []
        for loaded in self._loaded_plugins:
            all_contributions.extend(loaded.contributions)

        # Build resolved registry
        self._resolved_registry = build_registry(all_contributions)

        # Update registry state with resolved data
        self._registry.regions = self._resolved_registry.slots
        self._registry.commands = self._resolved_registry.commands
        self._registry.fingerprint = self._resolved_registry.fingerprint

        # Add conflicts and warnings from build report
        for conflict in self._resolved_registry.report.conflicts:
            self._registry.conflicts.append({
                "slot_id": conflict.slot_id,
                "winner": {
                    "plugin_id": conflict.winner.get("plugin_id"),
                    "priority": conflict.winner.get("priority", 100),
                    "discovery_index": conflict.winner.get("discovery_index"),
                },
                "losers": [
                    {
                        "plugin_id": l.get("plugin_id"),
                        "priority": l.get("priority", 100),
                        "discovery_index": l.get("discovery_index"),
                    }
                    for l in conflict.losers
                ],
            })

        self._registry.missing_required.extend(self._resolved_registry.report.missing_required)
        self._registry.warnings.extend(self._resolved_registry.report.warnings)
        self._registry.errors.extend(self._resolved_registry.report.errors)

        # Initialize command bus with resolved commands
        self._command_bus.load_commands_from_registry(self._registry.commands)

    def _should_degrade(self) -> bool:
        """Check if runtime should enter DEGRADED state."""
        # Check for required plugin failures
        for plugin in self._registry.plugins:
            if plugin.required and plugin.status == "FAILED":
                return True

        # Check for missing required slots
        if self._registry.missing_required:
            return True

        # Check for errors
        if self._registry.errors:
            return True

        return False

    # Registry access methods

    def get_registry_fingerprint(self) -> str:
        """Get the registry fingerprint."""
        return self._registry.fingerprint

    def get_perspectives(self) -> list[dict[str, Any]]:
        """Get perspectives as dicts for API response."""
        return [
            {
                "id": p.id,
                "label": p.label,
                "route_prefix": p.route_prefix,
                "description": p.description,
            }
            for p in self._registry.perspectives
        ]

    def get_regions(self) -> dict[str, list[dict[str, Any]]]:
        """Get regions with their contributions."""
        return self._registry.regions

    def get_regions_with_bundle_urls(self) -> dict[str, list[dict[str, Any]]]:
        """Get regions with bundle_url added to each contribution."""
        # Build a map of plugin_id -> bundle_url
        bundle_urls: dict[str, str | None] = {}
        for discovered in self._discovered_plugins:
            bundle = discovered.manifest.plugin.ui.bundle
            if bundle:
                bundle_urls[discovered.plugin_id] = f"/plugins/{discovered.plugin_id}/assets/{bundle}"
            else:
                bundle_urls[discovered.plugin_id] = None

        # Augment each contribution with bundle_url
        result: dict[str, list[dict[str, Any]]] = {}
        for slot_id, contributions in self._registry.regions.items():
            augmented_contributions = []
            for contrib in contributions:
                augmented = dict(contrib)
                plugin_id = augmented.get("plugin_id")
                if plugin_id and plugin_id in bundle_urls:
                    augmented["bundle_url"] = bundle_urls[plugin_id]
                augmented_contributions.append(augmented)
            result[slot_id] = augmented_contributions

        return result

    def get_commands(self) -> list[dict[str, Any]]:
        """Get registered commands."""
        return self._registry.commands

    def get_plugin_status(self) -> list[dict[str, Any]]:
        """Get plugin status list."""
        return [
            {
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "status": p.status,
                "discovery_index": p.discovery_index,
                "required": p.required,
                "error": p.error,
                "contribution_count": p.contribution_count,
                "load_time_ms": p.load_time_ms,
            }
            for p in self._registry.plugins
        ]

    def get_conflicts(self) -> list[dict[str, Any]]:
        """Get registry conflicts."""
        return self._registry.conflicts

    def get_missing_required(self) -> list[str]:
        """Get missing required slots."""
        return self._registry.missing_required

    def get_warnings(self) -> list[str]:
        """Get warnings."""
        return self._registry.warnings

    def get_errors(self) -> list[str]:
        """Get errors."""
        return self._registry.errors

    # Command execution methods

    async def execute_command(
        self, request: CommandExecuteRequest, user: UserContext | None = None
    ) -> CommandExecuteResult:
        """
        Execute a command.

        Args:
            request: The execution request
            user: The user context (defaults to anonymous)

        Returns:
            CommandExecuteResult with status and result/error
        """
        if user is None:
            user = UserContext.anonymous()
        return await self._command_bus.execute(request, user)

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent command audit log entries."""
        return self._command_bus.get_audit_log(limit)
