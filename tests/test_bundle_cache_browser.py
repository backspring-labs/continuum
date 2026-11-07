"""
A rebuilt plugin bundle reaches a real browser on a normal refresh (WebKit, as Safari).

The page here loads bundles the way the shell's ``loadBundle`` does: it reads
``/api/registry`` and adds each ``bundle_url`` as a module script. Skipped when
WebKit can't launch on the host.
"""

import os
import shutil
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi.responses import HTMLResponse

from continuum.main import create_app

playwright_api = pytest.importorskip("playwright.sync_api")

SAMPLE = Path(__file__).parents[1] / "plugins" / "continuum.sample_signal"
PLUGIN_ID = "continuum.sample_signal"
DAY = 24 * 3600

PAGE = (
    """<!doctype html><html><body><script type="module">
const registry = await (await fetch('/api/registry')).json();
const urls = new Set(Object.values(registry.regions).flat()
  .filter(c => c.plugin_id === '__PLUGIN__' && c.bundle_url).map(c => c.bundle_url));
for (const url of urls) {
  const s = document.createElement('script'); s.type = 'module'; s.src = url;
  document.head.appendChild(s);
}
</script></body></html>"""
).replace("__PLUGIN__", PLUGIN_ID)


def write_bundle(path: Path, build: int, age_s: int) -> None:
    path.write_text(f"document.body.dataset.build = '{build}';\n")
    stamp = time.time() - age_s
    os.utime(path, (stamp, stamp))


@pytest.fixture
def served(tmp_path, monkeypatch):
    """A Continuum server over one plugin whose bundle was deployed a day ago."""
    plugin = tmp_path / "plugins" / PLUGIN_ID
    shutil.copytree(SAMPLE, plugin, ignore=shutil.ignore_patterns("dist", "ui", "__pycache__"))
    (plugin / "dist").mkdir()
    bundle = plugin / "dist" / "plugin.js"
    write_bundle(bundle, 1, DAY)
    monkeypatch.chdir(tmp_path)

    app = create_app()
    app.add_api_route("/probe", lambda: HTMLResponse(PAGE), methods=["GET"])
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/probe", bundle
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def webkit_page():
    with playwright_api.sync_playwright() as p:
        try:
            browser = p.webkit.launch()
        except playwright_api.Error as exc:
            pytest.skip(f"WebKit can't launch here: {str(exc).splitlines()[0]}")
        yield browser.new_page()
        browser.close()


def build_shown(page) -> str:
    page.wait_for_function("document.body.dataset.build !== undefined", timeout=5000)
    return page.evaluate("document.body.dataset.build")


@pytest.mark.parametrize("arrive", ["reload", "navigate"])
def test_a_rebuilt_bundle_loads_on_a_normal_refresh(served, webkit_page, arrive):
    url, bundle = served
    webkit_page.goto(url)
    assert build_shown(webkit_page) == "1"

    write_bundle(bundle, 2, 0)
    if arrive == "reload":
        webkit_page.reload()
    else:
        webkit_page.goto("about:blank")
        webkit_page.goto(url)

    assert build_shown(webkit_page) == "2"
