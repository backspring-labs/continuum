"""
Acceptance tests for required/optional plugin and slot behavior.

These tests verify that:
1. Required plugin failures trigger DEGRADED state
2. Optional plugin failures stay in READY state
3. Required slot empty triggers DEGRADED state
4. Optional slot empty stays in READY state
5. Slot conflicts are resolved correctly (ONE cardinality)
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from continuum.app.discovery import discover_plugins
from continuum.app.loader import load_plugins
from continuum.app.registry import build_registry
from continuum.app.runtime import ContinuumRuntime, PluginStatus
from continuum.domain.lifecycle import LifecycleState
from continuum.domain.regions import RegionSpec, Cardinality, REGIONS


class TestRequiredPluginBehavior:
    """Test required plugin failure triggers DEGRADED state."""

    @pytest.mark.asyncio
    async def test_required_plugin_failure_triggers_degraded(self):
        """When a required plugin fails to load, runtime should be DEGRADED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a required plugin with invalid Python
            plugin_dir = Path(tmpdir) / "test.required_plugin"
            plugin_dir.mkdir()

            manifest = '''
[plugin]
id = "test.required_plugin"
name = "Required Test Plugin"
version = "1.0.0"
required = true

[plugin.ui]
tag_prefix = "test-required"
'''
            (plugin_dir / "plugin.toml").write_text(manifest)

            # Create an invalid __init__.py that will cause import error
            (plugin_dir / "__init__.py").write_text("raise ImportError('Simulated failure')")

            # Boot runtime with this plugin
            runtime = ContinuumRuntime(plugins_dir=tmpdir)
            await runtime.boot()

            # Should be DEGRADED due to required plugin failure
            assert runtime.lifecycle.state == LifecycleState.DEGRADED

    @pytest.mark.asyncio
    async def test_optional_plugin_failure_stays_ready(self):
        """When an optional plugin fails to load, runtime should stay READY."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an optional plugin with invalid Python
            plugin_dir = Path(tmpdir) / "test.optional_plugin"
            plugin_dir.mkdir()

            manifest = '''
[plugin]
id = "test.optional_plugin"
name = "Optional Test Plugin"
version = "1.0.0"
required = false

[plugin.ui]
tag_prefix = "test-optional"
'''
            (plugin_dir / "plugin.toml").write_text(manifest)

            # Create an invalid __init__.py that will cause import error
            (plugin_dir / "__init__.py").write_text("raise ImportError('Simulated failure')")

            # Boot runtime with this plugin
            runtime = ContinuumRuntime(plugins_dir=tmpdir)
            await runtime.boot()

            # Should still be READY despite optional plugin failure
            assert runtime.lifecycle.state == LifecycleState.READY

    @pytest.mark.asyncio
    async def test_mixed_plugins_required_failure_degrades(self):
        """When one required plugin fails among optional plugins, runtime should be DEGRADED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a working optional plugin
            optional_dir = Path(tmpdir) / "test.optional_ok"
            optional_dir.mkdir()

            optional_manifest = '''
[plugin]
id = "test.optional_ok"
name = "Working Optional Plugin"
version = "1.0.0"
required = false

[plugin.ui]
tag_prefix = "test-optional-ok"
'''
            (optional_dir / "plugin.toml").write_text(optional_manifest)
            (optional_dir / "__init__.py").write_text("# Working plugin")

            # Create a failing required plugin
            required_dir = Path(tmpdir) / "test.required_fail"
            required_dir.mkdir()

            required_manifest = '''
[plugin]
id = "test.required_fail"
name = "Failing Required Plugin"
version = "1.0.0"
required = true

[plugin.ui]
tag_prefix = "test-required-fail"
'''
            (required_dir / "plugin.toml").write_text(required_manifest)
            (required_dir / "__init__.py").write_text("raise ImportError('Simulated failure')")

            # Boot runtime
            runtime = ContinuumRuntime(plugins_dir=tmpdir)
            await runtime.boot()

            # Should be DEGRADED due to required plugin failure
            assert runtime.lifecycle.state == LifecycleState.DEGRADED


class TestRequiredSlotBehavior:
    """Test required slot empty triggers DEGRADED state."""

    @pytest.mark.asyncio
    async def test_required_slot_empty_triggers_degraded(self):
        """When a required slot has no contributions, runtime should be DEGRADED."""
        # Create a test region that is required
        test_regions = {
            **REGIONS,
            "ui.slot.required_test": RegionSpec(
                slot_id="ui.slot.required_test",
                cardinality=Cardinality.ONE,
                required=True,
                description="A required test slot",
            ),
        }

        with patch("continuum.app.registry.get_all_regions") as mock_regions, \
             patch("continuum.domain.regions.REGIONS", test_regions):
            # Return the test regions
            mock_regions.return_value = list(test_regions.values())

            with tempfile.TemporaryDirectory() as tmpdir:
                # Create a simple plugin that does NOT contribute to required slot
                plugin_dir = Path(tmpdir) / "test.simple_plugin"
                plugin_dir.mkdir()

                manifest = '''
[plugin]
id = "test.simple_plugin"
name = "Simple Plugin"
version = "1.0.0"

[plugin.ui]
tag_prefix = "test-simple"

[[contribution.panel]]
slot = "ui.slot.main"
component = "test-simple-panel"
'''
                (plugin_dir / "plugin.toml").write_text(manifest)
                (plugin_dir / "__init__.py").write_text("# Simple plugin")

                # Boot runtime
                runtime = ContinuumRuntime(plugins_dir=tmpdir)
                await runtime.boot()

                # Should be DEGRADED due to missing required slot
                assert runtime.lifecycle.state == LifecycleState.DEGRADED
                assert "ui.slot.required_test" in runtime.get_missing_required()

    @pytest.mark.asyncio
    async def test_optional_slot_empty_stays_ready(self):
        """When an optional slot has no contributions, runtime should stay READY."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple plugin
            plugin_dir = Path(tmpdir) / "test.simple_plugin"
            plugin_dir.mkdir()

            manifest = '''
[plugin]
id = "test.simple_plugin"
name = "Simple Plugin"
version = "1.0.0"

[plugin.ui]
tag_prefix = "test-simple"

[[contribution.panel]]
slot = "ui.slot.main"
component = "test-simple-panel"
'''
            (plugin_dir / "plugin.toml").write_text(manifest)
            (plugin_dir / "__init__.py").write_text("# Simple plugin")

            # Boot runtime - no contribution to right_rail which is optional
            runtime = ContinuumRuntime(plugins_dir=tmpdir)
            await runtime.boot()

            # Should be READY despite empty optional slot
            assert runtime.lifecycle.state == LifecycleState.READY


class TestSlotConflicts:
    """Test slot conflict resolution for ONE cardinality slots."""

    def test_one_slot_conflict_resolved_by_priority(self):
        """For ONE cardinality slots, higher priority wins."""
        contributions = [
            {
                "type": "panel",
                "slot": "ui.slot.header",  # ONE cardinality
                "priority": 50,
                "plugin_id": "low.priority",
                "discovery_index": 0,
                "component": "low-priority-header",
            },
            {
                "type": "panel",
                "slot": "ui.slot.header",
                "priority": 200,
                "plugin_id": "high.priority",
                "discovery_index": 1,
                "component": "high-priority-header",
            },
        ]

        registry = build_registry(contributions)

        # Header is ONE cardinality - should only have one contribution
        header_slot = registry.slots.get("ui.slot.header", [])
        assert len(header_slot) == 1
        assert header_slot[0]["plugin_id"] == "high.priority"

        # Should have a conflict report
        assert len(registry.report.conflicts) == 1
        conflict = registry.report.conflicts[0]
        assert conflict.slot_id == "ui.slot.header"
        assert conflict.winner["plugin_id"] == "high.priority"
        assert len(conflict.losers) == 1
        assert conflict.losers[0]["plugin_id"] == "low.priority"

    def test_one_slot_conflict_uses_discovery_index_as_tiebreaker(self):
        """For ONE cardinality slots with same priority, lower discovery index wins."""
        contributions = [
            {
                "type": "panel",
                "slot": "ui.slot.header",
                "priority": 100,
                "plugin_id": "later.discovery",
                "discovery_index": 10,
                "component": "later-header",
            },
            {
                "type": "panel",
                "slot": "ui.slot.header",
                "priority": 100,
                "plugin_id": "earlier.discovery",
                "discovery_index": 5,
                "component": "earlier-header",
            },
        ]

        registry = build_registry(contributions)

        header_slot = registry.slots.get("ui.slot.header", [])
        assert len(header_slot) == 1
        # Earlier discovery index wins the tie
        assert header_slot[0]["plugin_id"] == "earlier.discovery"

    def test_many_slot_no_conflict(self):
        """For MANY cardinality slots, all contributions are kept (no conflict)."""
        contributions = [
            {
                "type": "panel",
                "slot": "ui.slot.main",  # MANY cardinality
                "priority": 50,
                "plugin_id": "first.plugin",
                "discovery_index": 0,
                "component": "first-panel",
            },
            {
                "type": "panel",
                "slot": "ui.slot.main",
                "priority": 200,
                "plugin_id": "second.plugin",
                "discovery_index": 1,
                "component": "second-panel",
            },
            {
                "type": "panel",
                "slot": "ui.slot.main",
                "priority": 100,
                "plugin_id": "third.plugin",
                "discovery_index": 2,
                "component": "third-panel",
            },
        ]

        registry = build_registry(contributions)

        main_slot = registry.slots.get("ui.slot.main", [])
        # All three should be present
        assert len(main_slot) == 3
        # Sorted by priority (descending)
        assert main_slot[0]["plugin_id"] == "second.plugin"  # priority 200
        assert main_slot[1]["plugin_id"] == "third.plugin"   # priority 100
        assert main_slot[2]["plugin_id"] == "first.plugin"   # priority 50

        # No conflicts for MANY cardinality
        # (conflicts are only for ONE cardinality slots)
        main_conflicts = [c for c in registry.report.conflicts if c.slot_id == "ui.slot.main"]
        assert len(main_conflicts) == 0

    def test_one_slot_single_contribution_no_conflict(self):
        """For ONE cardinality slots with single contribution, no conflict."""
        contributions = [
            {
                "type": "panel",
                "slot": "ui.slot.header",
                "priority": 100,
                "plugin_id": "only.plugin",
                "discovery_index": 0,
                "component": "only-header",
            },
        ]

        registry = build_registry(contributions)

        header_slot = registry.slots.get("ui.slot.header", [])
        assert len(header_slot) == 1
        assert header_slot[0]["plugin_id"] == "only.plugin"

        # No conflict when there's only one contribution
        header_conflicts = [c for c in registry.report.conflicts if c.slot_id == "ui.slot.header"]
        assert len(header_conflicts) == 0


class TestPluginStatusTracking:
    """Test that plugin status is correctly tracked."""

    @pytest.mark.asyncio
    async def test_failed_plugin_status_recorded(self):
        """Failed plugins should have status='FAILED' in plugin list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a failing plugin
            plugin_dir = Path(tmpdir) / "test.failing_plugin"
            plugin_dir.mkdir()

            manifest = '''
[plugin]
id = "test.failing_plugin"
name = "Failing Plugin"
version = "1.0.0"
required = false

[plugin.ui]
tag_prefix = "test-failing"
'''
            (plugin_dir / "plugin.toml").write_text(manifest)
            (plugin_dir / "__init__.py").write_text("raise RuntimeError('Test failure')")

            runtime = ContinuumRuntime(plugins_dir=tmpdir)
            await runtime.boot()

            plugins = runtime.get_plugin_status()
            assert len(plugins) == 1
            assert plugins[0]["id"] == "test.failing_plugin"
            assert plugins[0]["status"] == "FAILED"
            assert plugins[0]["error"] is not None
            assert "Test failure" in plugins[0]["error"]

    @pytest.mark.asyncio
    async def test_loaded_plugin_status_recorded(self):
        """Successfully loaded plugins should have status='LOADED'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a working plugin
            plugin_dir = Path(tmpdir) / "test.working_plugin"
            plugin_dir.mkdir()

            manifest = '''
[plugin]
id = "test.working_plugin"
name = "Working Plugin"
version = "1.0.0"

[plugin.ui]
tag_prefix = "test-working"
'''
            (plugin_dir / "plugin.toml").write_text(manifest)
            (plugin_dir / "__init__.py").write_text("# Working plugin")

            runtime = ContinuumRuntime(plugins_dir=tmpdir)
            await runtime.boot()

            plugins = runtime.get_plugin_status()
            assert len(plugins) == 1
            assert plugins[0]["id"] == "test.working_plugin"
            assert plugins[0]["status"] == "LOADED"
            assert plugins[0]["error"] is None
