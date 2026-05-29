"""Day grouping helpers for parsed itinerary rows."""

from __future__ import annotations

from collections import OrderedDict

from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.group_tour_accommodation import _add_group_tour_accommodation_rows
from itinerary_generation.row_filters import is_optional_row


def group_rows_by_day(parsed_rows):
    grouped = {}

    for row in parsed_rows:
        if is_optional_row(row):
            continue

        day = row.get("day", "Unknown day")

        if day not in grouped:
            grouped[day] = []

        grouped[day].append(row)

    _add_group_tour_accommodation_rows(grouped)

    return OrderedDict(
        sorted(
            grouped.items(),
            key=lambda item: get_day_number(item[0]),
        )
    )


def get_day_count(grouped_days):
    return len(grouped_days)
