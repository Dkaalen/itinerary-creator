"""Stable source identity for Local Library workbook records."""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha1
import re

LOCAL_LIBRARY_AUTHORITY_ID = "bundled-local-library-workbook-v1"


def local_library_source_identity(values: Mapping[str, object]) -> str:
    """Return stable workbook/worksheet/row identity without display text."""

    workbook = _text(values.get("source_workbook"))
    worksheet = _text(values.get("source_sheet"))
    source_row = _source_row_text(values.get("source_row"))
    if not (workbook and worksheet and source_row):
        return ""
    return f"{LOCAL_LIBRARY_AUTHORITY_ID}:{workbook}:{worksheet}:{source_row}"


def stable_local_library_id(values: Mapping[str, object]) -> str:
    """Return a compact stable id based on source identity when available."""

    source_identity = local_library_source_identity(values)
    if source_identity:
        digest = sha1(source_identity.encode("utf-8")).hexdigest()[:12]
        prefix = _slug(values.get("source_sheet") or "library")
        return f"{prefix}_{digest}"

    # Synthetic test/import rows may not have workbook provenance. Keep a
    # deterministic fallback without affecting authoritative workbook rows.
    seed = "|".join(
        _text(values.get(key))
        for key in ("country", "category", "type", "travel_element", "supplier")
    )
    digest = sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"{_slug(values.get('country') or values.get('category') or 'library')}_{digest}"


def _source_row_text(value: object) -> str:
    if value in (None, ""):
        return ""
    try:
        return str(int(float(str(value))))
    except (TypeError, ValueError):
        return _text(value)


def _slug(value: object) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")
    return slug or "library"


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


__all__ = [
    "LOCAL_LIBRARY_AUTHORITY_ID",
    "local_library_source_identity",
    "stable_local_library_id",
]
