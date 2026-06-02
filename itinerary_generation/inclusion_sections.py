"""Categorized, client-facing inclusion summaries.

These helpers build the final inclusion page from parsed itinerary rows rather
than broad generic bullets. The functions are deterministic and presentation
focused; they do not change parser data.
"""

from __future__ import annotations

from collections import OrderedDict

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged, main_rows_only, has_self_drive_markers
from .inclusion_activities import activity_line, group_tour_overview_activity_lines
from .inclusion_hotels import hotel_line
from .inclusion_rentals import extract_rental_summary
from .inclusion_transport import (
    is_cruise_arrival_row,
    is_cruise_leisure_row,
    is_self_transfer_row,
    transport_bucket,
    transport_line,
)
from .inclusion_utils import add_unique, clean
from itinerary_generation.day_row_selectors import _is_empty_activity


def _is_rental_vehicle_text(row: dict) -> bool:
    text = f'{row.get("type", "")} {row.get("effective_type", "")} {row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    return any(marker in text for marker in [
        "rental car", "car rental", "rental vehicle", "pick up your rental",
        "pickup rental", "deliver your rental", "return your rental",
        "airport car rental office",
    ])


def create_categorized_inclusions(parsed_rows, grouped_days=None) -> list[dict]:
    """Return inclusion sections as [{title, items}]."""

    rows = main_rows_only(parsed_rows)
    sections: list[dict] = []

    hotel_items: list[str] = []
    activity_items: list[str] = []
    transport_buckets: OrderedDict[str, list[str]] = OrderedDict()

    if grouped_days:
        # Accommodation must read in itinerary order. Pull rows from the grouped
        # day structure because it contains synthetic group-tour overnights, and
        # because parsed_rows alone would put those placeholders after the real
        # post-tour hotel rows. Same-destination stays remain separate when they
        # occur at different points in the route.
        hotel_rows = []
        seen_hotel_keys = set()
        for day, day_rows in grouped_days.items():
            for row_index, row in enumerate(day_rows):
                if get_row_type(row) != "Hotel" or _is_rental_vehicle_text(row):
                    continue
                key = (
                    str(row.get("day", day)),
                    str(row.get("row_id", "")) or str(row_index),
                    clean(row.get("hotel_name") or row.get("title")).lower(),
                    clean(row.get("city", "")).lower(),
                )
                if key in seen_hotel_keys:
                    continue
                hotel_rows.append(row)
                seen_hotel_keys.add(key)
    else:
        hotel_rows = [row for row in rows if get_row_type(row) == "Hotel" and not _is_rental_vehicle_text(row)]
    activity_rows = [row for row in rows if get_row_type(row) == "Activity" and not _is_empty_activity(row)]

    for row in hotel_rows:
        add_unique(hotel_items, hotel_line(row))

    for row in activity_rows:
        add_unique(activity_items, activity_line(row))

    for item in group_tour_overview_activity_lines(rows):
        add_unique(activity_items, item)

    for row in rows:
        row_type = get_row_type(row)
        if row_type not in set(TRANSPORT_TYPES) | {"Transfer"}:
            continue
        text_for_skip = f'{row.get("title", "")} {row.get("details", "")}'.lower()
        if is_self_arranged(row) or is_self_transfer_row(row) or is_cruise_leisure_row(row) or is_cruise_arrival_row(row):
            continue
        if row_type == "Transfer" and text_for_skip.strip().startswith("arrival in") and "private" not in text_for_skip and "shuttle" not in text_for_skip:
            continue
        line = transport_line(row)
        if not line:
            continue
        bucket = transport_bucket(row)
        if not bucket:
            continue
        transport_buckets.setdefault(bucket, [])
        add_unique(transport_buckets[bucket], line)

    if hotel_items:
        sections.append({"title": "Accommodation", "items": hotel_items})
    if activity_items:
        sections.append({"title": "Activities & experiences", "items": activity_items})
    rental_items = extract_rental_summary(rows) if has_self_drive_markers(rows) else []
    if rental_items:
        sections.append({"title": "Rental vehicle", "items": rental_items})
    for bucket, items in transport_buckets.items():
        if items:
            sections.append({"title": bucket, "items": items})

    # Hotel meal plans are already shown under Accommodation. Keep the final
    # inclusions commercially clean by not repeating hotel dinners in a separate
    # Meals section unless a future parser adds standalone meal rows.

    # Guide/local-support details are already shown within each relevant day.
    # Keeping them off the commercial inclusions summary avoids repetition and
    # prevents self-guided experiences from being misrepresented as guided.
    return sections
