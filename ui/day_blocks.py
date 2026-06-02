"""Day block builders for itinerary HTML/UI output."""

import re

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_primary_city,
    get_row_type,
    is_optional_row,
    is_self_arranged,
)
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.title_safety import is_forbidden_client_title
from itinerary_generation.content_engine import client_activity_description, group_tour_pickup_window_from_overview, is_group_tour_overview, merge_compound_inclusions, sanitize_inclusion_item, clean_client_title
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer, get_transport_route_phrase
from itinerary_generation.canonical_builder import should_hide_note_row
from ui.canonical_blocks import render_accommodation_block, render_activity_block
from ui.day_overview_blocks import build_day_overview_block
from ui.simple_day_blocks import (
    build_arrival_block,
    build_cruise_leisure_block,
    build_departure_block,
    build_included_today_block,
    build_leisure_block,
)
from ui.optional_day_blocks import build_optional_day_block
from ui.transport_blocks import (
    build_self_arranged_travel_block,
    build_self_transfer_block,
    build_transport_block,
    build_travel_arrangements_block,
    get_travel_arrangement_line,
    get_travel_sequence_line,
    is_travel_sequence_candidate,
    _is_cruise_leisure_row,
)
from itinerary_generation.day_planner import plan_day
from text_polish import (
    strip_price_fragments,
    format_duration_display,
    polish_client_text,
    polish_hotel_name,
    polish_inclusion_item,
    polish_inclusion_items,
    polish_title,
)
from parser_modules.common import extract_route_points
from ui.activity_inclusions import (
    clean_activity_inclusion_items,
    get_fallback_activity_inclusions,
    prioritize_inline_inclusions,
)
from ui.render_helpers import (
    clean_space,
    display_time,
    display_time_with_duration,
    esc,
    get_activity_description,
    get_activity_duration_label,
    get_activity_logistics,
    get_detail_level_name,
    get_time_period,
    is_self_arranged_transport,
    is_self_transfer,
    is_tallinn_ferry_day_trip,
    meal_phrase,
    normalize_list,
    plural_nights,
    render_list_items,
)






def _is_group_tour_overview_row(row):
    return is_group_tour_overview(row)


def _format_time_range_from_start(hour, minute, suffix):
    start = f"{hour}:{minute} {suffix}"
    try:
        end_minute = int(minute) + 30
        end_hour = int(hour) + (1 if end_minute >= 60 else 0)
        end_minute = end_minute % 60
        if suffix == "PM" and end_hour > 12:
            end_hour -= 12
        return f"Between {start} and {end_hour}:{end_minute:02d} {suffix}"
    except Exception:
        return start


def _group_tour_start_time(rows):
    for row in rows:
        pickup = group_tour_pickup_window_from_overview(row)
        if pickup:
            return pickup
    return ""


def _supplier_day_description(row, max_sentences=6):
    """Use the actual supplier day prose for guided/group-tour day blocks.

    Generic fallbacks should only be used when supplier text is thin. For rows
    beginning ``Day N: ...`` we keep the first useful sentences after the
    heading, trimming marketing calls-to-action and optional add-on paragraphs.
    """

    source = str(row.get("details") or row.get("original_title") or "").strip()
    if not re.match(r"^\s*Day\s+\d+\s*[:\-–]", source, flags=re.IGNORECASE):
        return ""
    text = re.sub(r"^\s*Day\s+\d+\s*[:\-–]\s*[^\n]+", "", source, count=1, flags=re.IGNORECASE).strip()
    if not text:
        return ""
    text = re.split(r"\n\s*(?:What's included|What’s included|Not Included|Please note|Optional|What to expect)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.sub(r"\bBook this .*?$", "", text, flags=re.IGNORECASE | re.DOTALL)
    sentences = re.split(r"(?<=[.!?])\s+", clean_space(text))
    useful = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if any(marker in sentence.lower() for marker in ["what are you waiting", "book your", "check availability"]):
            continue
        useful.append(sentence)
        if len(useful) >= max_sentences:
            break
    return polish_client_text(" ".join(useful))



def _supplier_activity_description(row, max_sentences=4):
    """Extract useful supplier prose before falling back to generic copy."""
    day_specific = _supplier_day_description(row, max_sentences=max_sentences)
    if day_specific:
        return day_specific
    source = str(row.get("details") or row.get("original_title") or "").strip()
    if not source:
        return ""
    # Prefer What to expect, then Overview, then remaining prose after title line.
    candidates = []
    for marker in [r"What to expect\??", r"Overview"]:
        match = re.search(marker + r"\s*(.+)", source, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidates.append(match.group(1))
    if not candidates:
        # Supplier rows that contain only title/time/meeting/includes metadata
        # are not narrative descriptions. Let the planned fallback handle those.
        if not re.search(r"\b(overview|what to expect|description)\b", source, flags=re.IGNORECASE):
            if "|" in source or re.search(r"\btime\s*:", source, flags=re.IGNORECASE) or re.search(r"\bincludes?\s*:", source, flags=re.IGNORECASE):
                return ""
        candidates.append(source)
    for candidate in candidates:
        text = re.split(r"\n\s*(?:What's included|What’s included|Included With|Please note|Not included|Meeting Point|Pick up / meeting point|Pick-up / meeting point)\b", candidate, maxsplit=1, flags=re.IGNORECASE)[0]
        text = re.sub(r"^.*?\|\s*", "", text, count=1).strip() if "|" in text.split("\n", 1)[0] else text
        sentences = []
        for sentence in re.split(r"(?<=[.!?])\s+", clean_space(text)):
            sentence = sentence.strip()
            if not sentence:
                continue
            lower = sentence.lower()
            if any(bad in lower for bad in ["price is per", "please arrive", "book your", "check availability", "what are you waiting"]):
                continue
            sentences.append(sentence)
            if len(sentences) >= max_sentences:
                break
        if sentences:
            return polish_client_text(" ".join(sentences))
    return ""


def build_activity_block(row):
    return render_activity_block(row)








def build_accommodation_block(row):
    return render_accommodation_block(row)


def _is_blank_activity_row(row):
    if get_row_type(row) != "Activity":
        return False
    raw = clean_space(" ".join(str(row.get(key, "") or "") for key in ["title", "details", "original_title"] if str(row.get(key, "") or "").strip()))
    city = clean_space(row.get("city", ""))
    if not raw:
        return True
    lower = raw.lower().strip(" -:|")
    if city and lower == city.lower():
        return True
    def _matches_leisure(value):
        item = clean_space(value).lower().strip(" -:|")
        if not item:
            return False
        pattern = r"spend time at leisure\.?"
        if city:
            pattern = rf"(?:{re.escape(city.lower())}:?\s*)?{pattern}"
        return bool(re.fullmatch(pattern, item) or (city and re.fullmatch(rf"a day at leisure in {re.escape(city.lower())}\.?", item)))
    if any(_matches_leisure(row.get(key, "")) for key in ["title", "original_title", "details"]):
        return True
    leisure_pattern = r"spend time at leisure\.?"
    if city:
        leisure_pattern = rf"(?:{re.escape(city.lower())}:?\s*)?{leisure_pattern}"
    if re.fullmatch(leisure_pattern, lower):
        return True
    return bool(city and re.fullmatch(rf"a day at leisure in {re.escape(city.lower())}\.?", lower))

def build_day_blocks(rows):
    """Build day content in source order, grouping only consecutive travel rows.

    This prevents later/overnight travel from being pulled above daytime
    activities, while still keeping transfer + flight/train + transfer chains
    tidy and easy to read.
    """

    blocks = []
    travel_group = []
    main_rows = [row for row in rows if not is_optional_row(row)] or list(rows)
    day_plan = plan_day(main_rows)
    departure_day = any(get_row_type(row) == "Departure" for row in main_rows)
    has_activity = any(get_row_type(row) == "Activity" and not _is_blank_activity_row(row) for row in main_rows)
    group_tour_start_time = _group_tour_start_time(main_rows)

    def flush_travel_group():
        nonlocal travel_group
        if travel_group:
            block = build_travel_arrangements_block(travel_group)
            if block:
                blocks.append(block)
            travel_group = []

    for row in rows:
        row_type = get_row_type(row)
        title = row.get("title", "")

        if is_optional_row(row):
            flush_travel_group()
            blocks.append(build_optional_day_block(row))
            continue

        if is_travel_sequence_candidate(row):
            if departure_day and row_type == "Transfer" and "to your accommodation" in str(row.get("title", "")).lower():
                row = dict(row)
                city = get_primary_city(rows) or row.get("city", "")
                row["title"] = f"Private transfer from your hotel to {polish_title(city)} Airport" if city else "Private transfer from your hotel to the airport"
            travel_group.append(row)
            continue

        flush_travel_group()

        if row_type == "Departure":
            generic_departure = re.search(r"^(departure|departure\s+day|departure\s+home|journey\s+home)$", str(row.get("title", "")).strip(), flags=re.IGNORECASE)
            if not generic_departure:
                blocks.append(build_departure_block(row))
        elif row_type == "Day Overview":
            if has_activity and _is_group_tour_overview_row(row):
                continue
            block = build_day_overview_block(row)
            if block:
                blocks.append(block)
        elif row_type == "Car":
            block = build_day_overview_block(row)
            if block:
                blocks.append(block)
        elif row_type == "Hotel":
            blocks.append(build_accommodation_block(row))
        elif row_type == "Arrival":
            # Arrival titles/intros already welcome the traveller. Avoid adding
            # a second raw block like "Arrival / Welcome to Denmark".
            generic_arrival = re.search(r"^(arrival|welcome\s+to\s+.+)$", str(row.get("title", "")).strip(), flags=re.IGNORECASE)
            if not generic_arrival:
                blocks.append(build_arrival_block(row))
        elif row_type == "Activity":
            if _is_blank_activity_row(row):
                continue
            if group_tour_start_time and not row.get("time"):
                row = dict(row)
                row["group_tour_pickup_range"] = group_tour_start_time
            blocks.append(build_activity_block(row))
        elif row_type == "Leisure":
            if day_plan.suppress_free_time or (travel_group and len(rows) > 3):
                continue
            blocks.append(build_leisure_block(row))
        elif row_type in {"Notes", "Note"}:
            # Internal / operational notes must not leak into client-facing PDFs.
            if should_hide_note_row(row):
                continue
            continue
        elif _is_cruise_leisure_row(row):
            blocks.append(build_cruise_leisure_block(row))
        elif title:
            included_block = build_included_today_block([polish_title(title)])
            if included_block:
                blocks.append(included_block)

    flush_travel_group()
    return blocks
