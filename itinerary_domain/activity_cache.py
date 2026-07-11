"""Stable cache keys for activity product matching.

Activity product decisions are requested by titles, descriptions, inclusions,
validation and render builders.  Those callers often pass equivalent copies of
the same source row.  This module converts the relevant source-owned fields to a
small immutable snapshot so product matching can be cached safely without using
object identity or mutable dictionaries as cache keys.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_ACTIVITY_ROW_KEYS: tuple[str, ...] = (
    "raw",
    "original_title",
    "display_title",
    "title",
    "details",
    "description",
    "client_description",
    "city",
    "includes",
    "notable_sights",
    "route",
    "subtitle",
)


def _freeze_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _freeze_value(item)) for key, item in value.items()))
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze_value(item) for item in value), key=repr))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def freeze_activity_row(row: dict | None) -> tuple[tuple[str, Any], ...]:
    """Return only fields that can influence activity product identity."""

    if not row:
        return ()
    return tuple((key, _freeze_value(row.get(key))) for key in _ACTIVITY_ROW_KEYS if row.get(key) not in (None, "", [], (), {}))


def freeze_activity_values(values: tuple[object, ...]) -> tuple[Any, ...]:
    return tuple(_freeze_value(value) for value in values)


def _thaw_value(value: Any) -> Any:
    # Product matchers only need list-like ``includes`` values and scalar text.
    # Keep nested mappings immutable because no matcher mutates its inputs.
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def thaw_activity_row(snapshot: tuple[tuple[str, Any], ...]) -> dict[str, Any] | None:
    if not snapshot:
        return None
    return {key: _thaw_value(value) for key, value in snapshot}


def thaw_activity_values(snapshot: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(_thaw_value(value) for value in snapshot)
