"""Canonical activity block builder."""

from __future__ import annotations

import re

from itinerary_generation.canonical_helpers import _is_fløibanen, _row_id
from itinerary_generation.canonical_model import CanonicalBlock, CanonicalMetaLine
from itinerary_generation.content_engine import clean_client_title, client_activity_description, merge_compound_inclusions
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.tallinn import (
    clean_tallinn_ferry_inclusions,
    is_tallinn_ferry_framework,
    tallinn_departure_meta,
    tallinn_ferry_title,
)
from text_polish import format_duration_display, polish_client_text, polish_inclusion_items, strip_price_fragments
from itinerary_generation.activity_inclusions import clean_activity_inclusion_items, get_fallback_activity_inclusions, prioritize_inline_inclusions
from itinerary_generation.activity_description_helpers import get_activity_description
from itinerary_generation.activity_logistics import get_activity_logistics
from itinerary_generation.render_text_helpers import normalize_list
from itinerary_generation.product_rules import product_warning
from itinerary_generation.time_display import (
    display_time_with_duration,
    get_activity_duration_label,
    get_time_period,
)


def _activity_time_label(row: dict, time_display: str) -> str:
    """Return a client-facing label for activity timing details."""

    source = f"{row.get('title', '')} {row.get('original_title', '')} {row.get('details', '')}".lower()
    if time_display and " - " in time_display and ("anytime" in source or "flexible start" in source):
        return "Start window"
    return "Time"


def canonical_activity_block(row: dict, *, group_tour_pickup_range: str = "") -> CanonicalBlock:
    is_tallinn_ferry = is_tallinn_ferry_framework(row)
    title = normalize_client_day_title(create_client_activity_title(row) or "Experience", row)
    title = clean_client_title(title, row) or "Experience"
    if is_tallinn_ferry:
        title = tallinn_ferry_title(row)
    time = row.get("display_time") or row.get("time", "")
    duration = row.get("display_duration") or polish_client_text(row.get("duration", ""))
    meeting_label, meeting_point = get_activity_logistics(row)
    meeting_point = polish_client_text(meeting_point)
    end_point = polish_client_text(row.get("end_point", ""))
    notable_sights = polish_inclusion_items(normalize_list(row.get("notable_sights", [])), title)

    description_row = dict(row)
    description_row["display_title"] = title
    if is_tallinn_ferry:
        description = "Travel between Helsinki and Tallinn by ferry, with the crossings forming the logistics for your time in Tallinn."
    else:
        description = client_activity_description(description_row, get_activity_description(row))

    if is_tallinn_ferry:
        included_items = clean_tallinn_ferry_inclusions(row)
    else:
        included_items = clean_activity_inclusion_items(
            [strip_price_fragments(item) for item in row.get("includes", [])], title
        )
    fallback_items = [] if is_tallinn_ferry else get_fallback_activity_inclusions(row)
    if not included_items:
        included_items = fallback_items
    elif title == "Day Trip to Tallinn" and fallback_items:
        for item in fallback_items:
            if item not in included_items:
                included_items.append(item)
        if "Guided experience" in included_items and len(included_items) > 1:
            included_items = [item for item in included_items if item != "Guided experience"]
    included_items = list(dict.fromkeys(included_items))
    included_items = prioritize_inline_inclusions(merge_compound_inclusions(included_items), max_items=5)

    meta: list[CanonicalMetaLine] = []
    if is_tallinn_ferry:
        for label, value in tallinn_departure_meta(row):
            meta.append(CanonicalMetaLine(label, value))
    pickup_range = row.get("group_tour_pickup_range", "") or group_tour_pickup_range
    if pickup_range:
        meta.append(CanonicalMetaLine("Pick-up", pickup_range))
    elif not is_tallinn_ferry:
        time_display = time if row.get("display_time") else display_time_with_duration(time, duration)
        if time_display:
            meta.append(CanonicalMetaLine(_activity_time_label(row, time_display), time_display))

    if duration and not _is_fløibanen(title):
        meta.append(CanonicalMetaLine(get_activity_duration_label(row, duration), format_duration_display(duration)))
    if _is_fløibanen(title):
        meta.append(CanonicalMetaLine("Ticket", "Round-trip funicular ticket valid for a flexible visit to Mount Fløyen during the day."))
    if meeting_point:
        meta.append(CanonicalMetaLine(meeting_label, meeting_point))
    if end_point:
        meta.append(CanonicalMetaLine("End point", end_point))

    warnings: list[str] = []
    source_text = " ".join(str(row.get(key) or "") for key in ("raw", "original_title", "details", "title")).lower()
    warning_code, _warning_message = product_warning(row, source_text)
    if warning_code:
        warnings.append(warning_code)
    if "|" in description:
        warnings.append("description_contains_pipe")
    if re.search(r"\b(?:opening hours|includese|tickets only|carried out|participanter)\b", f"{title} {description}", re.I):
        warnings.append("raw_supplier_residue")

    return CanonicalBlock(
        kind="activity",
        row_id=_row_id(row),
        section_title="Ferry Journey" if is_tallinn_ferry else get_time_period(time),
        title=title,
        meta=meta,
        includes=included_items,
        description=description,
        notable_sights=notable_sights,
        source_row_ids=[_row_id(row)],
        warnings=warnings,
    )
