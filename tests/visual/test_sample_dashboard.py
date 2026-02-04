"""
Visual test for sample dashboard layout.

This test validates the sample dashboard HTML structure and can be extended
for visual regression testing with tools like Playwright or Puppeteer.

To view the dashboard manually:
    python -m http.server 8080 --directory tests/visual
    open http://localhost:8080/sample_dashboard.html

Or simply:
    open tests/visual/sample_dashboard.html
"""

import re
from pathlib import Path

VISUAL_DIR = Path(__file__).parent
DASHBOARD_HTML = VISUAL_DIR / "sample_dashboard.html"

# Expected regions (Switchboard slot IDs)
EXPECTED_REGIONS = [
    "ui.slot.left_nav",
    "ui.slot.header",
    "ui.slot.main",
    "ui.slot.right_rail",
    "ui.slot.footer",
    "ui.slot.modal",
]

# Expected sample panel contributions
EXPECTED_PANELS = [
    # Signal perspective
    "sample_signal.metric_1",
    "sample_signal.metric_2",
    "sample_signal.metric_3",
    "sample_signal.metric_4",
    "sample_signal.timeline",
    "sample_tasks.grid",
    # Right rail (all perspectives)
    "sample_activity.feed",
    "sample_tasks.active_list",
    # Systems perspective
    "systems.plugin_status",
    "systems.registry_inspector",
]


def test_dashboard_html_exists():
    """Dashboard HTML file exists."""
    assert DASHBOARD_HTML.exists(), f"Missing: {DASHBOARD_HTML}"


def test_dashboard_contains_all_regions():
    """Dashboard HTML contains all expected region slot labels."""
    content = DASHBOARD_HTML.read_text()
    for region in EXPECTED_REGIONS:
        assert region in content, f"Missing region: {region}"


def test_dashboard_contains_sample_panels():
    """Dashboard HTML contains sample panel placeholders."""
    content = DASHBOARD_HTML.read_text()
    for panel in EXPECTED_PANELS:
        assert panel in content, f"Missing panel: {panel}"


def test_dashboard_has_css_variables():
    """Dashboard uses CSS custom properties for theming."""
    content = DASHBOARD_HTML.read_text()
    expected_vars = [
        "--bg-base",
        "--bg-surface",
        "--text-primary",
        "--accent-primary",
        "--border-subtle",
        "--radius-md",
    ]
    for var in expected_vars:
        assert var in content, f"Missing CSS variable: {var}"


def test_dashboard_grid_layout():
    """Dashboard uses CSS grid for shell layout."""
    content = DASHBOARD_HTML.read_text()
    assert "display: grid" in content
    assert "grid-template-areas" in content
    # Grid includes left-nav, header, main, rail, footer
    assert "left-nav" in content
    assert "header" in content
    assert "main" in content
    assert "rail" in content
    assert "footer" in content


def test_dashboard_cardinality_indicators():
    """Dashboard shows cardinality indicators (ONE vs MANY)."""
    content = DASHBOARD_HTML.read_text()
    assert "MANY slot" in content, "Should indicate MANY cardinality for right_rail"


def test_dashboard_priority_indicators():
    """Dashboard shows priority ordering metadata."""
    content = DASHBOARD_HTML.read_text()
    # Check for priority values throughout the dashboard
    all_priorities = re.findall(r"[Pp]riority:\s*(\d+)", content)
    assert len(all_priorities) >= 4, "Should show priority values on panels"
    # Verify a range of priority values are demonstrated
    priority_values = set(int(p) for p in all_priorities)
    assert len(priority_values) >= 3, "Should demonstrate multiple priority levels"


def test_dashboard_no_reference_content():
    """Dashboard should not contain specific content from reference image."""
    content = DASHBOARD_HTML.read_text()
    # Should NOT contain specific names/text from the reference
    forbidden = ["SquadOps", "Lucas Garsten", "Eve Singer", "Nathan Jacobs", "Nebulus"]
    for term in forbidden:
        assert term not in content, f"Should not contain reference content: {term}"


def test_dashboard_has_left_nav_perspectives():
    """Dashboard has perspective switcher in left nav."""
    content = DASHBOARD_HTML.read_text()
    perspectives = ["signal", "research", "time", "discovery", "systems"]
    for perspective in perspectives:
        assert f'data-perspective="{perspective}"' in content, \
            f"Missing perspective: {perspective}"


def test_dashboard_has_interactive_actions():
    """Dashboard has interactive action triggers."""
    content = DASHBOARD_HTML.read_text()
    # Check for action functions
    assert "toggleOverlay()" in content, "Missing overlay toggle"
    assert "toggleChat()" in content, "Missing chat toggle"
    assert "simulateLogout()" in content, "Missing logout action"
    assert "switchPerspective(" in content, "Missing perspective switcher"


def test_dashboard_has_chat_panel():
    """Dashboard has slide-in chat panel."""
    content = DASHBOARD_HTML.read_text()
    assert "chat-panel" in content, "Missing chat panel"
    assert "Agent Assistant" in content, "Missing agent chat title"


def test_dashboard_has_command_palette_overlay():
    """Dashboard has command palette overlay."""
    content = DASHBOARD_HTML.read_text()
    assert "Command Palette" in content, "Missing command palette"
    assert "overlay" in content, "Missing overlay element"


def test_dashboard_title_is_continuum_builder():
    """Dashboard title should be Continuum Builder."""
    content = DASHBOARD_HTML.read_text()
    assert "Continuum Builder" in content, "Title should be 'Continuum Builder'"


if __name__ == "__main__":
    import subprocess
    import sys

    # Run with pytest if available, otherwise run basic checks
    try:
        sys.exit(subprocess.call(["pytest", __file__, "-v"]))
    except FileNotFoundError:
        print("Running basic checks (install pytest for full test output):\n")
        tests = [
            test_dashboard_html_exists,
            test_dashboard_contains_all_regions,
            test_dashboard_contains_sample_panels,
            test_dashboard_has_css_variables,
            test_dashboard_grid_layout,
            test_dashboard_cardinality_indicators,
            test_dashboard_priority_indicators,
            test_dashboard_no_reference_content,
        ]
        for test in tests:
            try:
                test()
                print(f"✓ {test.__doc__}")
            except AssertionError as e:
                print(f"✗ {test.__doc__}: {e}")
