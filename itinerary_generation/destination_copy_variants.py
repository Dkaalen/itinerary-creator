"""Deterministic destination copy variant selection."""
from __future__ import annotations

import hashlib


def stable_variant_index(*parts: object, count: int) -> int:
    if count <= 1:
        return 0
    digest = hashlib.sha1("|".join(str(part or "") for part in parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % count
