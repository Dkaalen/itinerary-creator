"""Shared helpers for structured input review."""

from __future__ import annotations

from typing import Any, Iterable, Mapping


def _rows(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(row) for row in rows or [] if isinstance(row, Mapping)]


def _text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _confidence(row: Mapping[str, Any]) -> int:
    value = row.get("parser_confidence", 100)
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 100
