"""Structured-document day builders."""

from __future__ import annotations

import re

from itinerary_generation.common import get_primary_city
from itinerary_generation.date_formatting import format_client_date
from itinerary_generation.group_tour_rendering import group_tour_day_city, group_tour_day_from_rows
from itinerary_generation.structured_model import DayDocument
from itinerary_generation.structured_row_helpers import _row_id

def _day_number(day: str) -> str:
    match = re.search(r"\d+", str(day or ""))
    return match.group(0) if match else str(day or "").strip()


def _build_days(
    grouped_days: dict[str, list[dict]],
    item_ids_by_row_id: dict[str, str],
    row_ids_by_object: dict[int, str],
) -> tuple[DayDocument, ...]:
    days: list[DayDocument] = []
    for day, rows in grouped_days.items():
        source_ids = tuple(row_ids_by_object.get(id(row), _row_id(row, index)) for index, row in enumerate(rows))
        item_ids = tuple(item_ids_by_row_id[row_id] for row_id in source_ids if row_id in item_ids_by_row_id)
        date = ""
        for row in rows:
            if row.get("start_date"):
                date = format_client_date(row.get("start_date"))
                break
        group_tour_destination = group_tour_day_city(rows) if group_tour_day_from_rows(rows) is not None else ""
        days.append(DayDocument(
            day=str(day),
            number=_day_number(str(day)),
            date=date,
            destination=group_tour_destination or get_primary_city(rows),
            item_ids=item_ids,
            source_row_ids=source_ids,
        ))
    return tuple(days)

__all__ = ["_day_number", "_build_days"]
