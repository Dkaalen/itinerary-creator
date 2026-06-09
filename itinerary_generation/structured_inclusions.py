"""Source-aware inclusion builder for the structured itinerary document.

The legacy inclusion builder returns display strings.  That was useful for the
old preview/PDF pages, but it loses the source-row identity that the new model
needs.  This module keeps each inclusion item tied to the row that produced it,
so a later title/detail cleanup cannot accidentally merge two different
activities or make one product overwrite another.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_row_type,
    has_self_drive_markers,
    is_optional_row,
    is_self_arranged,
    main_rows_only,
)
from itinerary_generation.day_row_selectors import _is_empty_activity
from itinerary_generation.inclusion_activities import activity_line, group_tour_overview_activity_lines
from itinerary_generation.inclusion_hotels import hotel_line
from itinerary_generation.inclusion_rentals import extract_rental_summary
from itinerary_generation.transport_domain.inclusions import (
    is_cruise_arrival_row,
    is_cruise_leisure_row,
    is_self_transfer_row,
    transport_bucket,
    transport_line,
)
from itinerary_generation.inclusion_utils import clean
from itinerary_generation.structured_model import StructuredListItem, StructuredListSection
from itinerary_generation.source_identity import source_row_id


def _row_id(row: dict, fallback_index: int = 0) -> str:
    return source_row_id(row, fallback_index)


def _source_row_id_for_inclusion(row: dict, row_indexes: dict[int, int], known_source_ids: set[str], fallback_index: int) -> str:
    """Return a valid source id, or blank for synthetic render-only rows."""

    explicit = str(row.get("row_id") or "").strip()
    if explicit and explicit in known_source_ids:
        return explicit
    if id(row) in row_indexes:
        return _row_id(row, row_indexes[id(row)])
    # Grouped-day structures can contain render-only synthetic rows. They should
    # still be displayed, but not with a fake source id that model validation
    # would correctly flag as missing.
    return ""


def _split_display_lines(value: str) -> tuple[str, tuple[str, ...]]:
    lines = [line.strip() for line in str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    if not lines:
        return "", ()
    return lines[0], tuple(lines[1:])


def _structured_item_from_line(
    line: str,
    *,
    source_row_id: str = "",
    category: str = "",
) -> StructuredListItem | None:
    label, detail_lines = _split_display_lines(line)
    if not label:
        return None
    source_ids = (source_row_id,) if source_row_id else ()
    return StructuredListItem(
        label=label,
        detail_lines=detail_lines,
        source_row_ids=source_ids,
        category=category,
    )


def _append_item_preserving_source(
    items: list[StructuredListItem],
    item: StructuredListItem | None,
) -> None:
    """Append an item unless the same source row already produced that label.

    The old inclusion path de-duplicated by display text only.  That is risky in
    a source-of-truth model because two real rows can have similar titles.  The
    new rule de-duplicates only when both label and source ids match; otherwise
    separate rows stay separate for review and rendering.
    """

    if item is None or not item.label:
        return
    key = (item.label.strip().lower(), tuple(item.source_row_ids), tuple(line.lower() for line in item.detail_lines))
    existing = {
        (current.label.strip().lower(), tuple(current.source_row_ids), tuple(line.lower() for line in current.detail_lines))
        for current in items
    }
    if key not in existing:
        items.append(item)


def _is_rental_vehicle_text(row: dict) -> bool:
    text = f'{row.get("type", "")} {row.get("effective_type", "")} {row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    return any(marker in text for marker in [
        "rental car", "car rental", "rental vehicle", "pick up your rental",
        "pickup rental", "deliver your rental", "return your rental",
        "airport car rental office",
    ])


def _hotel_rows_for_inclusions(rows: list[dict], grouped_days: dict[str, list[dict]] | None) -> list[dict]:
    if not grouped_days:
        return [row for row in rows if get_row_type(row) == "Hotel" and not _is_rental_vehicle_text(row)]

    hotel_rows: list[dict] = []
    seen_hotel_keys = set()
    for day, day_rows in grouped_days.items():
        for row_index, row in enumerate(day_rows):
            if is_optional_row(row) or get_row_type(row) != "Hotel" or _is_rental_vehicle_text(row):
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
    return hotel_rows


def _is_transport_candidate(row: dict) -> bool:
    row_type = get_row_type(row)
    text_for_skip = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    is_private_arrival_departure = (
        row_type in {"Arrival", "Departure"}
        and "private" in text_for_skip
        and any(marker in text_for_skip for marker in ["airport", "station", "hotel", "accommodation"])
    )
    if row_type not in set(TRANSPORT_TYPES) | {"Transfer"} and not is_private_arrival_departure:
        return False
    if is_self_arranged(row) or is_self_transfer_row(row) or is_cruise_leisure_row(row) or is_cruise_arrival_row(row):
        return False
    if row_type == "Transfer" and text_for_skip.strip().startswith("arrival in") and "private" not in text_for_skip and "shuttle" not in text_for_skip:
        return False
    return True


def build_structured_inclusion_sections(
    parsed_rows: Iterable[dict],
    grouped_days: dict[str, list[dict]] | None = None,
) -> tuple[StructuredListSection, ...]:
    """Return source-aware inclusion sections for the model and renderers."""

    source_rows = list(parsed_rows or [])
    rows = main_rows_only(source_rows)
    row_indexes = {id(row): index for index, row in enumerate(source_rows)}
    known_source_ids = {_row_id(row, index) for index, row in enumerate(source_rows)}

    accommodation_items: list[StructuredListItem] = []
    activity_items: list[StructuredListItem] = []
    rental_items: list[StructuredListItem] = []
    transport_buckets: OrderedDict[str, list[StructuredListItem]] = OrderedDict()

    for row in _hotel_rows_for_inclusions(rows, grouped_days):
        _append_item_preserving_source(
            accommodation_items,
            _structured_item_from_line(
                hotel_line(row),
                source_row_id=_source_row_id_for_inclusion(row, row_indexes, known_source_ids, len(accommodation_items)),
                category="accommodation",
            ),
        )

    for row in rows:
        if get_row_type(row) != "Activity" or _is_empty_activity(row) or row.get("group_tour_optional_extra"):
            continue
        _append_item_preserving_source(
            activity_items,
            _structured_item_from_line(
                activity_line(row),
                source_row_id=_source_row_id_for_inclusion(row, row_indexes, known_source_ids, len(activity_items)),
                category="activities",
            ),
        )

    for item in group_tour_overview_activity_lines(rows):
        _append_item_preserving_source(
            activity_items,
            _structured_item_from_line(item, category="activities"),
        )

    if has_self_drive_markers(rows):
        for index, item in enumerate(extract_rental_summary(rows)):
            _append_item_preserving_source(
                rental_items,
                _structured_item_from_line(item, category="rental_vehicle"),
            )

    for row in rows:
        if not _is_transport_candidate(row):
            continue
        line = transport_line(row)
        bucket = transport_bucket(row)
        if not line or not bucket:
            continue
        transport_buckets.setdefault(bucket, [])
        _append_item_preserving_source(
            transport_buckets[bucket],
            _structured_item_from_line(
                line,
                source_row_id=_source_row_id_for_inclusion(row, row_indexes, known_source_ids, 0),
                category="transport",
            ),
        )

    sections: list[StructuredListSection] = []
    if accommodation_items:
        sections.append(StructuredListSection("accommodation", "Accommodation", tuple(accommodation_items)))
    if activity_items:
        sections.append(StructuredListSection("activities", "Activities & experiences", tuple(activity_items)))
    if rental_items:
        sections.append(StructuredListSection("rental_vehicle", "Rental vehicle", tuple(rental_items)))
    for bucket, items in transport_buckets.items():
        section_id = "transport_" + "_".join(str(bucket).lower().split())
        if items:
            sections.append(StructuredListSection(section_id, bucket, tuple(items)))

    return tuple(sections)
