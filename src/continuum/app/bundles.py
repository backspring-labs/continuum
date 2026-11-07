"""
Content versions for plugin assets.

A plugin bundle is served from the same path on every deploy, so the path alone
can't tell a browser that the file changed. The registry gives each bundle URL a
``v`` taken from the file's bytes: a rebuilt bundle gets a new URL, and a URL
whose ``v`` matches the file on disk can be cached for good.
"""

import hashlib
from pathlib import Path

# Hex characters of the SHA-256 kept in a URL: 64 bits, ample to tell builds apart.
VERSION_LENGTH = 16


class AssetVersions:
    """The content version of each asset file, rehashed only when the file changes."""

    def __init__(self) -> None:
        self._known: dict[Path, tuple[tuple[int, int], str]] = {}

    def version_of(self, path: Path) -> str | None:
        """The file's content version, or None when it can't be read."""
        try:
            stat = path.stat()
            stamp = (stat.st_mtime_ns, stat.st_size)
            known = self._known.get(path)
            if known is not None and known[0] == stamp:
                return known[1]
            version = hashlib.sha256(path.read_bytes()).hexdigest()[:VERSION_LENGTH]
        except OSError:
            return None
        self._known[path] = (stamp, version)
        return version
