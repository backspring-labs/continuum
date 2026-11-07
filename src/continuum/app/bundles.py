"""
Content versions for plugin assets.

A plugin bundle is served from the same path on every deploy, so the path alone
can't tell a browser that the file changed. The registry gives each bundle URL a
``v`` taken from the file's bytes: a rebuilt bundle gets a new URL, and a URL
whose ``v`` matches the file on disk can be cached for good.

The bytes are hashed on every call. File metadata can't stand in for them: a
rebuild can write different bytes of the same length under a preserved
modification time, and a version reused from metadata would then name the old
file. Hashing a bundle costs well under a millisecond per 100 KB.
"""

import hashlib
from pathlib import Path

# Hex characters of the SHA-256 kept in a URL: 64 bits, ample to tell builds apart.
VERSION_LENGTH = 16


def content_version(path: Path) -> str | None:
    """The file's content version, or None when it can't be read."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()[:VERSION_LENGTH]
