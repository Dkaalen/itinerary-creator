"""Build canonical client-facing itinerary content before rendering.

This module is the bridge between parsed/normalized supplier rows and the UI.
All client-facing decisions should be made here or in ``content_engine`` before
HTML is generated.  Renderers should not choose raw supplier text directly.
"""
from __future__ import annotations

import re
from typing import Iterable

from itinerary_generation.canonical_model import CanonicalBlock, CanonicalDay, CanonicalMetaLine
from itinerary_generation.common import get_primary_city, get_row_type
from itinerary_generation.day_text import create_day_intro
from itinerary_generation.titles import create_day_title, create_client_activity_title, normalize_client_day_title
from itinerary_generation.content_engine import (
    clean_client_title,
    client_activity_description,
    group_tour_pickup_window_from_overview,
    is_group_tour_overview,
    merge_compound_inclusions,
    sanitize_inclusion_item,
    sanitize_supplier_prose,
    sanitize_day_intro,
    is_internal_note_text,
)
from text_polish import format_duration_display, polish_client_text, polish_hotel_name, polish_inclusion_items, polish_title, strip_price_fragments
from ui.render_helpers import (
    display_time_with_duration,
    get_activity_description,
    get_activity_duration_label,
    get_activity_logistics,
    get_time_period,
    meal_phrase,
    normalize_list,
    plural_nights,
)
from ui.final_pages import clean_activity_inclusion_items, get_fallback_activity_inclusions, prioritize_inline_inclusions


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _row_id(row: dict) -> str:
    return str(row.get("row_id") or "")


def _is_fløibanen(title: str) -> bool:
    lower = title.lower()
    return "fløibanen" in lower or "floibanen" in lower


def _group_tour_pickup_window(rows: Iterable[dict]) -> str:
    for row in rows:
        value = group_tour_pickup_window_from_overview(row)
        if value:
            return value
    return ""


def canonical_activity_block(row: dict, *, group_tour_pickup_range: str = "") -> CanonicalBlock:
    title = normalize_client_day_title(create_client_activity_title(row) or row.get("title", ""), row)
    title = clean_client_title(title, row)
    time = row.get("display_time") or row.get("time", "")
    duration = row.get("display_duration") or polish_client_text(row.get("duration", ""))
    meeting_label, meeting_point = get_activity_logistics(row)
    meeting_point = polish_client_text(meeting_point)
    end_point = polish_client_text(row.get("end_point", ""))
    notable_sights = polish_inclusion_items(normalize_list(row.get("notable_sights", [])), title)

    # Fallback is passed in only as a final fallback. Descriptions are composed
    # from canonical display facts so supplier paragraphs cannot pass through.
    description_row = dict(row)
    description_row["display_title"] = title
    description = client_activity_description(description_row, get_activity_description(row))

    included_items = clean_activity_inclusion_items(
        [strip_price_fragments(item) for item in row.get("includes", [])], title
    )
    fallback_items = get_fallback_activity_inclusions(row)
    if not included_items:
        included_items = fallback_items
    elif title == "Day Trip to Tallinn" and fallback_items:
        for item in fallback_items:
            if item not in included_items:
                included_items.append(item)
        if "Guided experience" in included_items and len(included_items) > 1:
            included_items = [item for item in included_items if item != "Guided experience"]
    included_items = prioritize_inline_inclusions(merge_compound_inclusions(included_items), max_items=5)

    meta: list[CanonicalMetaLine] = []
    pickup_range = row.get("group_tour_pickup_range", "") or group_tour_pickup_range
    if pickup_range:
        meta.append(CanonicalMetaLine("Pick-up", pickup_range))
    else:
        time_display = time if row.get("display_time") else display_time_with_duration(time, duration)
        if time_display:
            meta.append(CanonicalMetaLine("Time", time_display))

    if duration and not _is_fløibanen(title):
        meta.append(CanonicalMetaLine(get_activity_duration_label(row, duration), format_duration_display(duration)))
    if _is_fløibanen(title):
        meta.append(CanonicalMetaLine("Ticket", "Round-trip funicular ticket valid for a flexible visit to Mount Fløyen during the day."))
    if meeting_point:
        meta.append(CanonicalMetaLine(meeting_label, meeting_point))
    if end_point:
        meta.append(CanonicalMetaLine("End point", end_point))

    warnings: list[str] = []
    if "|" in description:
        warnings.append("description_contains_pipe")
    if re.search(r"\b(?:opening hours|includese|tickets only|carried out|participanter)\b", f"{title} {description}", re.I):
        warnings.append("raw_supplier_residue")

    return CanonicalBlock(
        kind="activity",
        row_id=_row_id(row),
        section_title=get_time_period(time),
        title=title,
        meta=meta,
        includes=included_items,
        description=description,
        notable_sights=notable_sights,
        source_row_ids=[_row_id(row)],
        warnings=warnings,
    )


def canonical_accommodation_block(row: dict) -> CanonicalBlock:
    hotel_name = polish_hotel_name(row.get("hotel_name") or row.get("title") or "Accommodation as listed")
    nights = plural_nights(row.get("hotel_nights", ""))
    room_category = polish_client_text(row.get("room_category") or "")
    if room_category.lower().strip() in {"self arranged", "self-arranged", "n/a", "na"}:
        room_category = ""
    meal = meal_phrase(row.get("meal_plan", ""))
    city = polish_title(row.get("city", ""))

    accommodation_line = polish_client_text(hotel_name if row.get("is_group_tour_accommodation") else f"{hotel_name} or similar")
    if city and city.lower() not in accommodation_line.lower():
        accommodation_line += f" in {city}"
    if nights:
        accommodation_line += f" for {nights}"

    lines: list[str] = []
    if room_category:
        line = f"Room category: {room_category}"
        if meal:
            line += f", {meal}"
        lines.append(line)
    elif meal:
        lines.append(meal.capitalize())

    return CanonicalBlock(
        kind="accommodation",
        row_id=_row_id(row),
        section_title="Overnight" if row.get("is_group_tour_accommodation") else "Accommodation",
        title=accommodation_line,
        lines=lines,
        source_row_ids=[_row_id(row)],
    )


def canonical_day(day: str, rows: list[dict], *, output_edits: dict | None = None, detail_level: str = "Rich descriptive") -> CanonicalDay:
    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    title = day_edits.get("title") or create_day_title(rows)
    intro = day_edits.get("intro") or create_day_intro(rows, detail_level=detail_level)
    city = day_edits.get("city") or get_primary_city(rows)
    if not city and any(get_row_type(row) == "Cruise" for row in rows):
        city = "Cruise"
    number = str(day).replace("Day", "").strip() or str(day).strip()
    return CanonicalDay(
        day=day,
        number=number,
        city=polish_title(city),
        title=clean_client_title(title, rows[0] if rows else {}),
        intro=sanitize_day_intro(intro, rows),
        source_row_ids=[_row_id(row) for row in rows if _row_id(row)],
    )


def should_hide_note_row(row: dict) -> bool:
    text = f"{row.get('title','')} {row.get('details','')} {row.get('original_title','')}"
    return is_internal_note_text(text)


def canonical_included_items(items: Iterable[str]) -> list[str]:
    return [item for item in (sanitize_inclusion_item(item) for item in items) if item]
