"""
Tests for dynamic plugin UI loading.

These tests verify that:
1. Plugin bundles are served correctly from the assets endpoint
2. The registry includes bundle_url for contributions
3. Custom elements are registered in the browser (E2E)
"""

import pytest


class TestPluginAssetServing:
    """Tests for the plugin assets endpoint."""

    def test_plugin_bundle_served(self, client):
        """Plugin JS bundle is served from assets endpoint."""
        response = client.get("/plugins/continuum.sample_signal/assets/plugin.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")
        # Verify it contains custom element registrations
        assert "customElements.define" in response.text

    def test_plugin_bundle_content_type(self, client):
        """Plugin bundle has correct content-type header."""
        response = client.get("/plugins/continuum.sample_systems/assets/plugin.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")

    def test_nonexistent_plugin_returns_404(self, client):
        """Nonexistent plugin returns 404."""
        response = client.get("/plugins/nonexistent.plugin/assets/plugin.js")
        assert response.status_code == 404

    def test_nonexistent_asset_returns_404(self, client):
        """Nonexistent asset in valid plugin returns 404."""
        response = client.get("/plugins/continuum.sample_signal/assets/nonexistent.js")
        assert response.status_code == 404

    def test_path_traversal_blocked(self, client):
        """Path traversal attempts are blocked."""
        response = client.get(
            "/plugins/continuum.sample_signal/assets/../../../etc/passwd"
        )
        # Should be blocked - either 400 or 403 or 404
        assert response.status_code in (400, 403, 404)

    def test_invalid_plugin_id_rejected(self, client):
        """Invalid plugin IDs with path traversal are rejected."""
        response = client.get("/plugins/../continuum.sample_signal/assets/plugin.js")
        # Should be blocked
        assert response.status_code in (400, 403, 404)


class TestRegistryBundleUrls:
    """Tests for bundle_url in registry response."""

    def test_registry_includes_bundle_urls(self, client):
        """Registry response includes bundle_url for contributions."""
        response = client.get("/api/registry")
        assert response.status_code == 200

        data = response.json()
        regions = data.get("regions", {})

        # Find a contribution that should have a bundle_url
        main_panels = regions.get("ui.slot.main", [])
        signal_panels = [p for p in main_panels if p.get("perspective") == "signal"]

        # At least one signal panel should exist
        assert len(signal_panels) > 0

        # Panels from sample_signal should have bundle_url
        for panel in signal_panels:
            if panel.get("plugin_id") == "continuum.sample_signal":
                assert "bundle_url" in panel
                assert panel["bundle_url"].endswith("/assets/plugin.js")
                assert "continuum.sample_signal" in panel["bundle_url"]

    def test_plugins_without_bundles_have_null_bundle_url(self, client):
        """Plugins without bundles have null bundle_url."""
        response = client.get("/api/registry")
        assert response.status_code == 200

        data = response.json()
        regions = data.get("regions", {})

        # sample_nav doesn't have a bundle
        nav_items = regions.get("ui.slot.left_nav", [])
        for nav in nav_items:
            if nav.get("plugin_id") == "continuum.sample_nav":
                # Should have bundle_url key but it should be null
                assert nav.get("bundle_url") is None


class TestPluginBundleContent:
    """Tests for the content of plugin bundles."""

    def test_signal_plugin_defines_expected_elements(self, client):
        """Signal plugin bundle defines expected custom elements."""
        response = client.get("/plugins/continuum.sample_signal/assets/plugin.js")
        assert response.status_code == 200

        content = response.text
        # Should define at least one signal component
        assert "continuum-sample-signal" in content

    def test_systems_plugin_defines_expected_elements(self, client):
        """Systems plugin bundle defines expected custom elements."""
        response = client.get("/plugins/continuum.sample_systems/assets/plugin.js")
        assert response.status_code == 200

        content = response.text
        # Should define at least one systems component
        assert "continuum-sample-systems" in content

    def test_chat_plugin_defines_expected_elements(self, client):
        """Chat plugin bundle defines expected custom elements."""
        response = client.get("/plugins/continuum.sample_chat/assets/plugin.js")
        assert response.status_code == 200

        content = response.text
        # Should define the chat drawer component
        assert "continuum-sample-chat-drawer" in content


# E2E tests that require a browser (Playwright) and running servers
# Run with: pytest tests/test_plugin_loading.py::TestE2ECustomElements -v
# Requires: backend (port 4040) and frontend (port 5173) running

def _servers_running():
    """Check if both backend and frontend servers are running."""
    import urllib.request
    import urllib.error
    urls = ["http://localhost:4040/health", "http://localhost:5173"]
    for url in urls:
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=2):
                pass
        except (urllib.error.URLError, TimeoutError):
            return False
    return True


@pytest.mark.skipif(not _servers_running(), reason="Requires backend (4040) and frontend (5173) servers running")
class TestE2ECustomElements:
    """E2E tests for custom element rendering in the browser."""

    def test_custom_element_in_dom(self, page):
        """Custom element appears in DOM after shell loads."""
        page.goto("http://localhost:5173")

        # Wait for the shell to load
        page.wait_for_load_state("networkidle")

        # Wait for a custom element to appear
        page.wait_for_selector("continuum-sample-signal-metrics", timeout=10000)

        # Check for custom elements
        metrics = page.query_selector("continuum-sample-signal-metrics")
        assert metrics is not None

    def test_custom_element_renders_content(self, page):
        """Custom element renders its content in shadow DOM."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Wait for element to be defined
        page.wait_for_function(
            "customElements.get('continuum-sample-signal-metrics') !== undefined",
            timeout=10000
        )

        # Check shadow DOM content
        content = page.evaluate("""
            () => {
                const el = document.querySelector('continuum-sample-signal-metrics');
                if (!el || !el.shadowRoot) return null;
                return el.shadowRoot.textContent;
            }
        """)
        assert content is not None
        assert len(content) > 0  # Has some content

    def test_switching_perspectives_loads_different_bundles(self, page):
        """Switching perspectives loads different plugin bundles."""
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # Start in signal perspective - wait for signal components
        page.wait_for_selector("continuum-sample-signal-metrics", timeout=10000)

        # Click Systems nav item (the button containing the tooltip text)
        page.click('button:has-text("Systems")')

        # Wait for systems components to load
        page.wait_for_selector("continuum-sample-systems-plugins", timeout=10000)

        # Verify systems components are present
        plugins_panel = page.query_selector("continuum-sample-systems-plugins")
        assert plugins_panel is not None
