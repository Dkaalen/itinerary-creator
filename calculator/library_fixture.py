"""Read-only bundled Local Library fallback rows."""

from __future__ import annotations

import json
from dataclasses import fields
from functools import lru_cache
from importlib import resources
from typing import Any

from calculator.library_model import LocalLibraryRow

_FALLBACK_JSON_PACKAGE = "calculator.data"
_FALLBACK_JSON_NAME = "local_library_fallback.json"
_ROW_FIELDS = {field.name for field in fields(LocalLibraryRow)}


@lru_cache(maxsize=1)
def fallback_library_rows() -> tuple[LocalLibraryRow, ...]:
    """Return bundled read-only rows for missing Local Library credentials."""

    return tuple(_row_from_mapping(item) for item in _load_fallback_rows())


def _load_fallback_rows() -> list[dict[str, Any]]:
    payload = resources.files(_FALLBACK_JSON_PACKAGE).joinpath(_FALLBACK_JSON_NAME).read_text(encoding="utf-8")
    data = json.loads(payload)
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _row_from_mapping(item: dict[str, Any]) -> LocalLibraryRow:
    values = {key: item[key] for key in _ROW_FIELDS.intersection(item)}
    return LocalLibraryRow(**values)
