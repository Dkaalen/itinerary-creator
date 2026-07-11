"""Annotate supplier programme-day rows when the package master is absent.

A source row beginning with ``Day N:`` is a supplier-owned programme segment.
That identity does not disappear merely because a partial export omitted its
package master row.  This module assigns the same canonical day contract used
by complete group-tour packages, while recording that package context is
incomplete.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Mapping

from itinerary_generation.group_tour_day_parser import build_group_tour_day
from itinerary_generation.group_tour_row_helpers import _group_tour_day_source, _row_type


_ALLOWED_ROW_TYPES = {"activity", "group tour"}


def _is_orphan_programme_day(row: Mapping[str, Any]) -> bool:
    row_type = _row_type(row).casefold()
    if row_type not in _ALLOWED_ROW_TYPES:
        return False
    source = _group_tour_day_source(row)
    return source.lstrip().casefold().startswith("day ") and ":" in source.splitlines()[0]


def annotate_orphan_group_tour_days(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_name: str = "",
) -> list[dict[str, Any]]:
    """Attach canonical day-segment metadata to partial programme exports.

    Rows without an explicit supplier ``Day N`` heading remain untouched.  The
    inferred package duration is only display context; it is never used to
    invent missing package days or package-level inclusions.
    """

    updated = [dict(row) for row in rows or ()]
    segments: list[tuple[dict[str, Any], object]] = []
    for row in updated:
        if not _is_orphan_programme_day(row):
            continue
        segment = build_group_tour_day(row, source_name=source_name)
        segment = replace(
            segment,
            warnings=tuple(dict.fromkeys((*segment.warnings, "group_tour_package_master_missing"))),
        )
        segments.append((row, segment))

    if not segments:
        return updated

    duration = max(segment.package_day_number for _, segment in segments)
    context = {
        "package_id": "",
        "title": "",
        "season": "unknown",
        "duration_days": duration,
        "itinerary_start_day": min(
            (segment.itinerary_day_number for _, segment in segments if segment.itinerary_day_number),
            default=0,
        ),
        "itinerary_end_day": max(
            (segment.itinerary_day_number for _, segment in segments if segment.itinerary_day_number),
            default=0,
        ),
        "meeting_point": "",
        "pickup_time": "",
        "group_style": "supplier_programme",
        "commercial_status": "included",
        "warnings": ["group_tour_package_master_missing"],
    }
    for row, segment in segments:
        row["group_tour_role"] = "day_segment"
        row["group_tour_day"] = segment.as_metadata
        row["group_tour_package_day"] = segment.package_day_number
        row["group_tour_itinerary_day"] = segment.itinerary_day_number
        row["group_tour_package_context"] = context
    return updated


__all__ = ["annotate_orphan_group_tour_days"]
