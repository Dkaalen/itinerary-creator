"""Cleaning helpers for Norway in a Nutshell domain objects."""

from __future__ import annotations

from typing import Any

from place_aliases import canonicalize_place_name
from text_polish import polish_title


def _clean_place(value: Any) -> str:
    return canonicalize_place_name(polish_title(str(value or "").strip(" -:|.,")))


def _clean_strings(values: Any) -> tuple[str, ...]:
    if not values:
        return ()
    if isinstance(values, str):
        values = [values]
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _clean_places(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in values or ():
        place = _clean_place(value)
        if place and (not result or result[-1].lower() != place.lower()):
            result.append(place)
    return tuple(result)


__all__ = ["_clean_place", "_clean_places", "_clean_strings"]
