"""Payload cleaning for saved itinerary projects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from app_modules.saved_project_constants import BANNED_RECURSIVE_KEYS, BANNED_SESSION_KEYS


_IMAGE_UPLOAD_KEYS = frozenset({"upload", "replacement_upload"})


def clean_project_value(value: Any) -> Any:
    """Return a JSON-safe project value without transient or preview-heavy fields."""

    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in BANNED_SESSION_KEYS or key_text in BANNED_RECURSIVE_KEYS:
                continue
            if key_text in _IMAGE_UPLOAD_KEYS and _upload_carries_preview_data(item):
                continue
            cleaned[key_text] = clean_project_value(item)
        return cleaned

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [clean_project_value(item) for item in value]

    if isinstance(value, (bytes, bytearray)):
        return ""

    return deepcopy(value)


def clean_output_edits(output_edits: Mapping[str, Any] | None) -> dict[str, Any]:
    return clean_project_value(output_edits or {})


def clean_parsed_rows(parsed_rows: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    cleaned = clean_project_value(list(parsed_rows or []))
    return [row for row in cleaned if isinstance(row, dict)]


def _upload_carries_preview_data(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(key in value for key in ("data_uri", "base64", "b64", "bytes"))
