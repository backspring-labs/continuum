"""
M1 Integration tests - Plugin discovery, loading, and registry resolution.
"""

import tempfile
import os
from pathlib import Path

import pytest

from continuum.app.discovery import discover_plugins, DiscoveredPlugin
from continuum.app.loader import load_plugins, PluginContext
from continuum.app.registry import build_registry


class TestPluginDiscovery:
    """Test plugin discovery functionality."""

    def test_discovery_order_is_alphabetical(self):
        """Plugins should be discovered in alphabetical order by directory name."""
        discovery = discover_plugins("./plugins")

        plugin_ids = [p.plugin_id for p in discovery.plugins]

        # Should be alphabetically sorted by directory name
        assert plugin_ids == [
            "continuum.sample_chat",
            "continuum.sample_command",
            "continuum.sample_diagnostics",
            "continuum.sample_nav",
            "continuum.sample_signal",
            "continuum.sample_systems",
        ]

    def test_discovery_index_assigned(self):
        """Each plugin should have a unique discovery_index."""
        discovery = discover_plugins("./plugins")

        indices = [p.discovery_index for p in discovery.plugins]
        assert indices == [0, 1, 2, 3, 4, 5]

    def test_missing_plugins_dir_produces_warning(self):
        """Missing plugins directory should produce a warning, not error."""
        discovery = discover_plugins("./nonexistent_plugins_dir")

        assert len(discovery.plugins) == 0
        assert len(discovery.warnings) == 1
        assert "not found" in discovery.warnings[0]

    def test_directory_mismatch_produces_error(self):
        """Directory name not matching plugin ID should produce an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create plugin with mismatched directory name
            plugin_dir = Path(tmpdir) / "wrong_name"
            plugin_dir.mkdir()

            manifest = '''
[plugin]
id = "correct.plugin_name"
name = "Test"
version = "1.0.0"

[plugin.ui]
tag_prefix = "correct-plugin-name"
'''
            (plugin_dir / "plugin.toml").write_text(manifest)

            discovery = discover_plugins(tmpdir)

            assert len(discovery.plugins) == 0
            assert len(discovery.errors) == 1
            assert "does not match plugin ID" in discovery.errors[0]


class TestPluginLoader:
    """Test plugin loading functionality."""

    def test_plugins_load_in_discovery_order(self):
        """Plugins should load in the same order they were discovered."""
        discovery = discover_plugins("./plugins")
        load_result = load_plugins(discovery.plugins)

        loaded_ids = [p.plugin_id for p in load_result.plugins]
        discovered_ids = [p.plugin_id for p in discovery.plugins]

        assert loaded_ids == discovered_ids

    def test_all_sample_plugins_load_successfully(self):
        """All sample plugins should load without errors."""
        discovery = discover_plugins("./plugins")
        load_result = load_plugins(discovery.plugins)

        assert len(load_result.errors) == 0
        for plugin in load_result.plugins:
            assert plugin.status == "LOADED", f"Plugin {plugin.plugin_id} failed: {plugin.error}"

    def test_plugin_contributions_registered(self):
        """Plugins should register their contributions."""
        discovery = discover_plugins("./plugins")
        load_result = load_plugins(discovery.plugins)

        # Check that sample_nav registered 7 contributions
        nav_plugin = next(p for p in load_result.plugins if p.plugin_id == "continuum.sample_nav")
        assert len(nav_plugin.contributions) == 7


class TestPluginContext:
    """Test the PluginContext used for contribution registration."""

    def test_contribution_includes_plugin_metadata(self):
        """Registered contributions should include plugin ID and discovery_index."""
        ctx = PluginContext("test.plugin", 42)
        ctx.register_contribution("panel", {"slot": "ui.slot.main", "component": "test"})

        contributions = ctx.get_contributions()
        assert len(contributions) == 1
        assert contributions[0]["plugin_id"] == "test.plugin"
        assert contributions[0]["discovery_index"] == 42
        assert contributions[0]["type"] == "panel"


class TestRegistryBuilder:
    """Test registry resolution."""

    def test_contributions_sorted_by_priority(self):
        """Contributions should be sorted by priority (highest first)."""
        contributions = [
            {"type": "panel", "slot": "ui.slot.main", "priority": 50, "plugin_id": "a", "discovery_index": 0},
            {"type": "panel", "slot": "ui.slot.main", "priority": 200, "plugin_id": "b", "discovery_index": 1},
            {"type": "panel", "slot": "ui.slot.main", "priority": 100, "plugin_id": "c", "discovery_index": 2},
        ]

        registry = build_registry(contributions)
        main_slot = registry.slots["ui.slot.main"]

        assert main_slot[0]["plugin_id"] == "b"  # priority 200
        assert main_slot[1]["plugin_id"] == "c"  # priority 100
        assert main_slot[2]["plugin_id"] == "a"  # priority 50

    def test_discovery_index_breaks_priority_ties(self):
        """Discovery index should break ties when priorities are equal."""
        contributions = [
            {"type": "panel", "slot": "ui.slot.main", "priority": 100, "plugin_id": "second", "discovery_index": 5},
            {"type": "panel", "slot": "ui.slot.main", "priority": 100, "plugin_id": "first", "discovery_index": 2},
        ]

        registry = build_registry(contributions)
        main_slot = registry.slots["ui.slot.main"]

        # Lower discovery_index wins when priority is equal
        assert main_slot[0]["plugin_id"] == "first"
        assert main_slot[1]["plugin_id"] == "second"

    def test_fingerprint_is_deterministic(self):
        """Registry fingerprint should be deterministic."""
        contributions = [
            {"type": "panel", "slot": "ui.slot.main", "priority": 100, "plugin_id": "a", "discovery_index": 0},
            {"type": "panel", "slot": "ui.slot.main", "priority": 200, "plugin_id": "b", "discovery_index": 1},
        ]

        registry1 = build_registry(contributions)
        registry2 = build_registry(contributions)

        assert registry1.fingerprint == registry2.fingerprint

    def test_fingerprint_changes_with_different_contributions(self):
        """Registry fingerprint should change when contributions change."""
        contrib1 = [
            {"type": "panel", "slot": "ui.slot.main", "priority": 100, "plugin_id": "a", "discovery_index": 0},
        ]
        contrib2 = [
            {"type": "panel", "slot": "ui.slot.main", "priority": 100, "plugin_id": "b", "discovery_index": 0},
        ]

        registry1 = build_registry(contrib1)
        registry2 = build_registry(contrib2)

        assert registry1.fingerprint != registry2.fingerprint


class TestIntegration:
    """End-to-end integration tests with sample plugins."""

    def test_full_pipeline_with_sample_plugins(self):
        """Test complete discovery -> load -> resolve pipeline."""
        # Discover
        discovery = discover_plugins("./plugins")
        assert len(discovery.plugins) == 6

        # Load
        load_result = load_plugins(discovery.plugins)
        assert all(p.status == "LOADED" for p in load_result.plugins)

        # Collect contributions
        all_contributions = []
        for loaded in load_result.plugins:
            all_contributions.extend(loaded.contributions)
        assert len(all_contributions) == 17  # Total from all sample plugins

        # Build registry
        registry = build_registry(all_contributions)

        # Verify left_nav has 7 items in correct priority order
        left_nav = registry.slots["ui.slot.left_nav"]
        assert len(left_nav) == 7
        priorities = [c.get("priority", 100) for c in left_nav]
        assert priorities == sorted(priorities, reverse=True)  # Descending order

    def test_registry_fingerprint_stable_across_boots(self):
        """Registry fingerprint should be stable across multiple discovery/load cycles."""
        fingerprints = []

        for _ in range(3):
            discovery = discover_plugins("./plugins")
            load_result = load_plugins(discovery.plugins)
            all_contributions = []
            for loaded in load_result.plugins:
                all_contributions.extend(loaded.contributions)
            registry = build_registry(all_contributions)
            fingerprints.append(registry.fingerprint)

        assert len(set(fingerprints)) == 1  # All fingerprints should be identical
