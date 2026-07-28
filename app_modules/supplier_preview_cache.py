"""Exact-source cache for parsed supplier rows and parser diagnostics."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any

SUPPLIER_PREVIEW_CACHE_KEY = "_supplier_preview_cache_v1"


@dataclass(frozen=True)
class SupplierRowsPreview:
    rows: tuple[dict[str, Any], ...]
    parser_diagnostics: tuple[dict[str, Any], ...] = ()


def supplier_source_signature(raw_text: object) -> str:
    return hashlib.sha256(str(raw_text or "").encode("utf-8")).hexdigest()


def cached_supplier_rows_preview(
    state: Mapping[str, Any],
    raw_text: object,
) -> SupplierRowsPreview | None:
    source_text = str(raw_text or "")
    if not source_text.strip():
        return None
    cached = state.get(SUPPLIER_PREVIEW_CACHE_KEY)
    if not isinstance(cached, Mapping):
        return None
    if cached.get("signature") != supplier_source_signature(source_text):
        return None
    rows = cached.get("rows")
    diagnostics_items = cached.get("parser_diagnostics")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return None
    if not isinstance(diagnostics_items, Sequence) or isinstance(
        diagnostics_items, (str, bytes, bytearray)
    ):
        diagnostics_items = ()
    return SupplierRowsPreview(
        rows=tuple(dict(row) for row in rows if isinstance(row, Mapping)),
        parser_diagnostics=tuple(
            dict(item) for item in diagnostics_items if isinstance(item, Mapping)
        ),
    )


def remember_supplier_rows_preview(
    state: MutableMapping[str, Any],
    raw_text: object,
    rows: Sequence[Mapping[str, Any]],
    *,
    parser_diagnostics: Sequence[Mapping[str, Any]] = (),
) -> SupplierRowsPreview | None:
    source_text = str(raw_text or "")
    if not source_text.strip():
        clear_supplier_preview_cache(state)
        return None
    preview = SupplierRowsPreview(
        rows=tuple(dict(row) for row in rows if isinstance(row, Mapping)),
        parser_diagnostics=tuple(
            dict(item) for item in parser_diagnostics if isinstance(item, Mapping)
        ),
    )
    state[SUPPLIER_PREVIEW_CACHE_KEY] = {
        "signature": supplier_source_signature(source_text),
        "rows": [dict(row) for row in preview.rows],
        "parser_diagnostics": [dict(item) for item in preview.parser_diagnostics],
    }
    return preview


def clear_supplier_preview_cache(state: MutableMapping[str, Any]) -> None:
    state.pop(SUPPLIER_PREVIEW_CACHE_KEY, None)


__all__ = [
    "SUPPLIER_PREVIEW_CACHE_KEY",
    "SupplierRowsPreview",
    "cached_supplier_rows_preview",
    "clear_supplier_preview_cache",
    "remember_supplier_rows_preview",
    "supplier_source_signature",
]
