"""
Plugin bundle URLs carry their content version, so a rebuilt bundle reaches the browser.

A bundle is served from one path on every deploy. Without a version in the URL, a
browser holding the old file can keep using it after a rebuild.
"""

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from continuum.app.bundles import content_version
from continuum.main import create_app

SAMPLE = Path(__file__).parents[1] / "plugins" / "continuum.sample_signal"
PLUGIN_ID = "continuum.sample_signal"


@pytest.fixture
def plugins_root(tmp_path, monkeypatch):
    """A plugins directory holding one sample plugin with a built bundle, as the cwd."""
    plugin = tmp_path / "plugins" / PLUGIN_ID
    shutil.copytree(SAMPLE, plugin, ignore=shutil.ignore_patterns("dist", "ui", "__pycache__"))
    (plugin / "dist").mkdir()
    (plugin / "dist" / "plugin.js").write_text("export const build = 1;\n")
    monkeypatch.chdir(tmp_path)
    return plugin


@pytest.fixture
def client(plugins_root):
    with TestClient(create_app()) as client:
        yield client


def bundle_url(client) -> str:
    regions = client.get("/api/registry").json()["regions"]
    urls = {
        c["bundle_url"]
        for contributions in regions.values()
        for c in contributions
        if c.get("plugin_id") == PLUGIN_ID
    }
    assert len(urls) == 1, urls
    return urls.pop()


def test_a_rebuilt_bundle_gets_a_new_url(client, plugins_root):
    first = bundle_url(client)
    assert first.startswith(f"/plugins/{PLUGIN_ID}/assets/plugin.js?v=")

    (plugins_root / "dist" / "plugin.js").write_text("export const build = 2;\n")
    second = bundle_url(client)

    assert second != first
    assert client.get(second).text == "export const build = 2;\n"


@pytest.mark.parametrize(
    ("query", "cache_control"),
    [
        ("current", "public, max-age=31536000, immutable"),
        ("", "no-cache"),
        ("?v=0123456789abcdef", "no-cache"),
    ],
    ids=["current version", "no version", "stale version"],
)
def test_only_the_current_version_is_cached_for_good(client, query, cache_control):
    """A stale v gets today's bytes, which must not be kept under yesterday's URL."""
    url = (
        bundle_url(client)
        if query == "current"
        else f"/plugins/{PLUGIN_ID}/assets/plugin.js{query}"
    )

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["cache-control"] == cache_control


def test_an_unchanged_bundle_answers_304(client):
    url = bundle_url(client)
    etag = client.get(url).headers["etag"]

    unchanged = client.get(url, headers={"If-None-Match": etag})
    changed = client.get(url, headers={"If-None-Match": '"some-other-build"'})

    assert unchanged.status_code == 304
    assert unchanged.content == b""
    assert unchanged.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert changed.status_code == 200


def test_the_registry_is_revalidated(client):
    """It carries the versions: a cached copy would point the shell at old bundles."""
    assert client.get("/api/registry").headers["cache-control"] == "no-cache"


def test_a_missing_bundle_has_an_unversioned_url_and_answers_404(client, plugins_root):
    (plugins_root / "dist" / "plugin.js").unlink()

    url = bundle_url(client)

    assert url == f"/plugins/{PLUGIN_ID}/assets/plugin.js"
    assert client.get(url).status_code == 404


def test_a_rebuild_keeping_length_and_timestamp_still_gets_a_new_url(client, plugins_root):
    """A rebuild can write same-length bytes under a preserved mtime: metadata can't stand in."""
    bundle = plugins_root / "dist" / "plugin.js"
    first = bundle_url(client)
    stamp = bundle.stat()

    bundle.write_text("export const build = 9;\n")
    os.utime(bundle, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert (bundle.stat().st_size, bundle.stat().st_mtime_ns) == (stamp.st_size, stamp.st_mtime_ns)
    second = bundle_url(client)

    assert second != first
    assert client.get(second).headers["cache-control"] == "public, max-age=31536000, immutable"
    assert client.get(first).headers["cache-control"] == "no-cache"


def test_an_unreadable_asset_has_no_version(tmp_path):
    assert content_version(tmp_path / "absent.js") is None
    assert content_version(tmp_path) is None
