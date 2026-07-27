"""Canonical activity block builder."""

from __future__ import annotations

import re

from itinerary_generation.activity_identity_contract import resolve_activity_identity
from itinerary_generation.canonical_helpers import _is_fløibanen, _row_id
from itinerary_generation.canonical_model import CanonicalBlock, CanonicalMetaLine
from itinerary_generation.content_engine import clean_client_title, client_activity_description, merge_compound_inclusions
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.tallinn import (
    clean_tallinn_ferry_inclusions,
    is_tallinn_ferry_framework,
    tallinn_departure_meta,
    tallinn_ferry_title,
    tallinn_ferry_description,
)
from text_polish import format_duration_display, polish_client_text, polish_inclusion_items, strip_price_fragments
from itinerary_generation.activity_inclusions import clean_activity_inclusion_items, get_fallback_activity_inclusions, prioritize_inline_inclusions
from itinerary_generation.activity_description_helpers import get_activity_description
from itinerary_generation.activity_logistics import get_activity_logistics
from itinerary_generation.render_text_helpers import normalize_list
from itinerary_generation.product_rules import product_warning
from shared.source_text_cleanup import clean_supplier_list, clean_supplier_text, clean_supplier_title
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


def _suppress_duration_when_time_range_is_clear(row: dict, time_display: str, duration: str) -> bool:
    source = f"{row.get('title', '')} {row.get('original_title', '')} {row.get('details', '')} {row.get('client_description', '')}".lower()
    duration_text = str(duration or "").lower()
    if not time_display or " - " not in time_display or not duration_text:
        return False
    # Fjord/ferry day trips often mention a one-way sailing time in supplier
    # prose. When the actual activity already has a full start/end time, showing
    # the one-way value as the total duration is misleading.
    return bool(re.search(r"\bone[- ]way\b|\bper\s+direction\b", source))


def _format_clock_time(value: str) -> str:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(value or "").strip())
    if not match:
        return str(value or "").strip()
    hour = int(match.group(1))
    minute = match.group(2)
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute} {suffix}"


def _timezone_specific_cruise_time(row: dict) -> str:
    """Keep supplier timezone distinctions for cross-border cruise products."""

    source = " ".join(str(row.get(key) or "") for key in ("raw", "original_title", "details", "title"))
    match = re.search(
        r"(?:\bcruise\s*time\s*:?\s*)?(?P<s1>\d{1,2}:\d{2})\s*[-–—]\s*(?P<s2>\d{1,2}:\d{2})\s*swedish\s*/\s*(?P<f1>\d{1,2}:\d{2})\s*[-–—]\s*(?P<f2>\d{1,2}:\d{2})(?:\s*finnish)?",
        source,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    swedish = f"{_format_clock_time(match.group('s1'))} - {_format_clock_time(match.group('s2'))} Swedish time"
    finnish = f"{_format_clock_time(match.group('f1'))} - {_format_clock_time(match.group('f2'))} Finnish time"
    return f"{swedish} / {finnish}"



def _important_activity_note(row: dict) -> str:
    """Preserve commercial/safety notes that should not be lost in prose polish."""

    source = " ".join(str(row.get(key) or "") for key in ("details", "original_title", "title"))
    if re.search(r"\bwithout\s+meals?\b", source, flags=re.IGNORECASE):
        return "Meals are not included with this experience."
    if re.search(r"\b(?:cannot|can not|can't)\s+guarantee\b.*?\bwhales?\b|\bwhale\s+sightings?\s+(?:cannot|can not|can't)\s+be\s+guaranteed\b", source, flags=re.IGNORECASE):
        return "Whale sightings cannot be guaranteed and depend on migration patterns and conditions."
    return ""

def canonical_activity_block(row: dict, *, group_tour_pickup_range: str = "") -> CanonicalBlock:
    is_tallinn_ferry = is_tallinn_ferry_framework(row)
    identity = resolve_activity_identity(row)
    product_title = identity.display_title if identity.source in {"normalized_product", "product_registry"} else ""
    if product_title:
        title = clean_supplier_title(product_title) or "Experience"
    else:
        title = normalize_client_day_title(create_client_activity_title(row) or "Experience", row)
        title = clean_supplier_title(clean_client_title(title, row) or "Experience")
    if is_tallinn_ferry:
        title = tallinn_ferry_title(row)
    time = row.get("display_time") or row.get("time", "")
    duration = row.get("display_duration") or polish_client_text(row.get("duration", ""))
    meeting_label, meeting_point = get_activity_logistics(row)
    meeting_point = clean_supplier_text(polish_client_text(meeting_point))
    if meeting_point.strip().lower() in {"x", "xx", "xxx", "n/a", "na", "tbc", "tbd", "-"}:
        meeting_point = ""
    end_point = clean_supplier_text(polish_client_text(row.get("end_point", "")))
    notable_sights = polish_inclusion_items(normalize_list(row.get("notable_sights", [])), title)

    description_row = dict(row)
    description_row["display_title"] = title
    if is_tallinn_ferry:
        description = tallinn_ferry_description(row)
    else:
        description = client_activity_description(description_row, get_activity_description(row))
    if _is_fløibanen(title):
        description = re.sub(r"\bMount\s+Fløibanen\b", "Mount Fløyen", description)
        description = re.sub(r"\bMount\s+Floibanen\b", "Mount Fløyen", description, flags=re.IGNORECASE)

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
    included_items = [re.sub(r"\b(Admission|Ticket|Tour|Transfer)\s+\1\b", r"\1", item, flags=re.IGNORECASE) for item in included_items]
    included_items = clean_supplier_list(dict.fromkeys(included_items))
    # Keep ordinary supplier inclusions complete on day pages. Seven/eight
    # short bullets are still readable and avoid source/output mismatches where
    # the day page drops items that later appear in the inclusion summary.
    included_items = prioritize_inline_inclusions(merge_compound_inclusions(included_items), max_items=8)

    meta: list[CanonicalMetaLine] = []
    if is_tallinn_ferry:
        for label, value in tallinn_departure_meta(row):
            meta.append(CanonicalMetaLine(label, value))
    pickup_range = row.get("group_tour_pickup_range", "") or group_tour_pickup_range
    if pickup_range:
        meta.append(CanonicalMetaLine("Pick-up", pickup_range))
    elif not is_tallinn_ferry:
        timezone_cruise_time = _timezone_specific_cruise_time(row)
        if timezone_cruise_time:
            meta.append(CanonicalMetaLine("Cruise time", timezone_cruise_time))
        else:
            time_display = time if row.get("display_time") else display_time_with_duration(time, duration)
            if time_display:
                meta.append(CanonicalMetaLine(_activity_time_label(row, time_display), time_display))

    if duration and not _is_fløibanen(title) and not _suppress_duration_when_time_range_is_clear(row, time_display if 'time_display' in locals() else display_time_with_duration(time, duration), duration):
        meta.append(CanonicalMetaLine(get_activity_duration_label(row, duration), format_duration_display(duration)))
    if _is_fløibanen(title):
        meta.append(CanonicalMetaLine("Ticket", "Round-trip funicular ticket valid for a flexible visit to Mount Fløyen during the day."))
    if meeting_point:
        meta.append(CanonicalMetaLine(meeting_label, meeting_point))
    if end_point:
        meta.append(CanonicalMetaLine("End point", end_point))
    important_note = _important_activity_note(row)
    if important_note:
        meta.append(CanonicalMetaLine("Notes", polish_client_text(important_note)))

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
        description=clean_supplier_text(description),
        notable_sights=notable_sights,
        source_row_ids=[_row_id(row)],
        warnings=warnings,
    )
