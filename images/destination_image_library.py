"""Destination image-library review helpers.

The app already owns image matching and replacement selection.  This module
builds a small consultant-facing summary for image workflow screens and tests:
which days are matched, which depend on fallback/low-score images, and where
replacement options exist.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class DestinationImageLibraryDay:
    day: str
    city: str
    status: str
    current_path: str = ""
    score: int = 0
    replacement_options: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _city_for_rows(rows: Iterable[Mapping[str, Any]] | None) -> str:
    for row in rows or []:
        if isinstance(row, Mapping):
            city = str(row.get("city") or row.get("destination") or row.get("location") or "").strip()
            if city:
                return city
    return ""


def _score(match: Mapping[str, Any] | None) -> int:
    try:
        return int((match or {}).get("score") or 0)
    except (TypeError, ValueError):
        return 0


def image_library_day_rows(
    grouped_days: Mapping[str, Iterable[Mapping[str, Any]]] | None,
    image_matches: Mapping[str, Mapping[str, Any] | None] | None,
    replacement_options_by_day: Mapping[str, Iterable[Any]] | None = None,
) -> tuple[DestinationImageLibraryDay, ...]:
    image_matches = image_matches or {}
    replacement_options_by_day = replacement_options_by_day or {}
    rows: list[DestinationImageLibraryDay] = []
    for day, day_rows in (grouped_days or {}).items():
        day_key = str(day)
        match = image_matches.get(day_key) if isinstance(image_matches, Mapping) else None
        options = tuple(replacement_options_by_day.get(day_key) or ())
        path = str((match or {}).get("path") or "") if isinstance(match, Mapping) else ""
        data_uri = bool((match or {}).get("data_uri")) if isinstance(match, Mapping) else False
        score = _score(match)
        if not (path or data_uri):
            status = "missing"
        elif isinstance(match, Mapping) and match.get("is_default"):
            status = "fallback"
        elif score and score < 45:
            status = "low_score"
        elif options:
            status = "replaceable"
        else:
            status = "ready"
        rows.append(DestinationImageLibraryDay(
            day=day_key,
            city=_city_for_rows(day_rows),
            status=status,
            current_path=path,
            score=score,
            replacement_options=len(options),
        ))
    return tuple(rows)
