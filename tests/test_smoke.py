"""
M0 Smoke tests - verify lifecycle boots to READY state.
"""

import pytest
from fastapi.testclient import TestClient

from continuum.main import app
from continuum.domain import LifecycleState


class TestLifecycleBoot:
    """Test that the runtime boots through lifecycle stages correctly."""

    @pytest.fixture
    def client(self):
        """Create test client with lifespan."""
        with TestClient(app) as client:
            yield client

    def test_health_endpoint_returns_ready(self, client):
        """Health endpoint should return lifecycle_state: ready after boot."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["lifecycle_state"] == "ready"

    def test_diagnostics_endpoint_no_errors(self, client):
        """Diagnostics should show no errors after clean boot."""
        response = client.get("/diagnostics")
        assert response.status_code == 200
        data = response.json()
        assert data["lifecycle_state"] == "ready"
        assert data["errors"] == []

    def test_registry_has_perspectives(self, client):
        """Registry should contain built-in perspectives."""
        response = client.get("/api/registry")
        assert response.status_code == 200
        data = response.json()

        perspectives = data["perspectives"]
        assert len(perspectives) == 5

        perspective_ids = {p["id"] for p in perspectives}
        assert perspective_ids == {"signal", "research", "time", "discovery", "systems"}

    def test_registry_has_regions(self, client):
        """Registry should contain all region slots."""
        response = client.get("/api/registry")
        assert response.status_code == 200
        data = response.json()

        regions = data["regions"]
        expected_slots = {
            "ui.slot.left_nav",
            "ui.slot.header",
            "ui.slot.main",
            "ui.slot.right_rail",
            "ui.slot.footer",
            "ui.slot.modal",
            "ui.slot.drawer",
            "ui.slot.toast_stack",
        }
        assert set(regions.keys()) == expected_slots

    def test_registry_has_fingerprint(self, client):
        """Registry should have a deterministic fingerprint."""
        response = client.get("/api/registry")
        assert response.status_code == 200
        data = response.json()

        fingerprint = data["registry_fingerprint"]
        assert fingerprint is not None
        assert len(fingerprint) == 16  # SHA256 truncated to 16 chars

    def test_registry_fingerprint_is_deterministic(self, client):
        """Registry fingerprint should be the same across requests."""
        response1 = client.get("/api/registry")
        response2 = client.get("/api/registry")

        assert response1.json()["registry_fingerprint"] == response2.json()["registry_fingerprint"]


class TestManifestValidation:
    """Test plugin manifest validation."""

    def test_valid_manifest(self):
        """Valid manifest should pass validation."""
        from continuum.domain import validate_manifest

        data = {
            "plugin": {
                "id": "acme.dashboard",
                "name": "ACME Dashboard",
                "version": "1.0.0",
                "description": "Dashboard plugin",
                "required": False,
                "ui": {"tag_prefix": "acme-dashboard"},
            },
            "contributions": {
                "nav": [
                    {
                        "slot": "ui.slot.left_nav",
                        "perspective": "signal",
                        "label": "Dashboard",
                        "target": {"type": "panel", "panel_id": "main"},
                    }
                ],
                "panel": [
                    {
                        "slot": "ui.slot.main",
                        "perspective": "signal",
                        "component": "dashboard-main",
                    }
                ],
            },
        }

        result = validate_manifest(data)
        assert result.valid
        assert result.manifest is not None
        assert result.manifest.plugin.id == "acme.dashboard"

    def test_invalid_plugin_id_format(self):
        """Plugin ID must be vendor.plugin_name format."""
        from continuum.domain import validate_manifest

        data = {
            "plugin": {
                "id": "no-dot-here",
                "name": "Bad Plugin",
                "version": "1.0.0",
                "ui": {"tag_prefix": "bad-plugin"},
            }
        }

        result = validate_manifest(data)
        assert not result.valid
        assert len(result.errors) > 0

    def test_invalid_slot_reference(self):
        """Invalid slot references should be caught."""
        from continuum.domain import validate_manifest

        data = {
            "plugin": {
                "id": "acme.test",
                "name": "Test Plugin",
                "version": "1.0.0",
                "ui": {"tag_prefix": "acme-test"},
            },
            "contributions": {
                "nav": [
                    {
                        "slot": "ui.slot.nonexistent",
                        "label": "Bad Nav",
                        "target": {"type": "panel", "panel_id": "test"},
                    }
                ]
            },
        }

        result = validate_manifest(data)
        assert not result.valid
        assert any("Invalid nav slot" in e for e in result.errors)

    def test_tag_prefix_mismatch_warning(self):
        """Mismatched tag_prefix should produce a warning."""
        from continuum.domain import validate_manifest

        data = {
            "plugin": {
                "id": "acme.dashboard",
                "name": "ACME Dashboard",
                "version": "1.0.0",
                "ui": {"tag_prefix": "wrong-prefix"},
            }
        }

        result = validate_manifest(data)
        assert result.valid  # Still valid, just warning
        assert len(result.warnings) > 0
        assert any("tag_prefix" in w for w in result.warnings)
