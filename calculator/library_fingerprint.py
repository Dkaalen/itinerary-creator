"""Content fingerprints for the authoritative Local Library workbook."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

WORKBOOK_FINGERPRINT_VERSION = "xlsx-sha256-v1"


def local_library_workbook_fingerprint(path: str | Path) -> str:
    """Return a content-based fingerprint that cannot miss same-size rewrites."""

    workbook_path = Path(path)
    digest = sha256()
    with workbook_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"{WORKBOOK_FINGERPRINT_VERSION}:{digest.hexdigest()}"


__all__ = ["WORKBOOK_FINGERPRINT_VERSION", "local_library_workbook_fingerprint"]
