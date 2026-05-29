"""Travel-arrangement sequence block builders."""

from __future__ import annotations

import re

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.content_engine import clean_client_title
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer, get_premium_transport_phrase
from text_polish import (
    strip_price_fragments,
    format_duration_display,
    polish_client_text,
    polish_inclusion_items,
    polish_title,
)
from ui.day_overview_blocks import _polish_overview_item
from ui.render_helpers import clean_space, display_time, normalize_list, render_list_items
from ui.transport_row_blocks import _is_cruise_leisure_row


def _transport_route_phrase(row):
    return get_premium_transport_phrase(row)

def is_travel_sequence_candidate(row):
    """Rows that form chronological travel arrangements within a day."""

    row_type = get_row_type(row)
    if _is_cruise_leisure_row(row):
        return False
    return row_type == "Transfer" or row_type in TRANSPORT_TYPES

def get_travel_sequence_line(row):
    row_type = get_row_type(row)

    if row_type == "Transfer" and is_self_arranged(row):
        title = _clean_self_arranged_travel_title(get_transfer_travel_title(row) or row.get("title", "Self-arranged travel"))
        return f"{title} (self-arranged, not included)"

    if row_type in TRANSPORT_TYPES and is_self_arranged(row):
        title = _clean_self_arranged_travel_title(row.get("title", "Self-arranged travel"))
        if row_type == "Flight" and title.lower().startswith("flight"):
            return f"Self-arranged {title[0].lower() + title[1:]} (not included)"
        return f"{title} (self-arranged, not included)"

    if row_type == "Transfer" and is_route_transfer(row):
        return polish_title(get_transfer_travel_title(row) or row.get("title", ""))

    if row_type == "Transfer":
        return clean_client_title(row.get("title", ""), row)

    if row_type in TRANSPORT_TYPES:
        phrase = get_premium_transport_phrase(row)
        return polish_title(phrase or row.get("title", ""))

    return polish_title(row.get("title", ""))

def _clean_self_arranged_travel_title(title):
    text = polish_title(strip_price_fragments(str(title or "")))
    text = re.sub(r"\s*,?\s*(?:cost|price)\s+not\s+included\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,?\s*self[-\s]?arranged\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,-:|")
    return polish_title(text)

def _extract_timed_route_places(row):
    text = str(row.get("details") or row.get("original_title") or row.get("title") or "")
    places = []
    for raw in text.replace("|", "\n").splitlines():
        line = clean_space(raw)
        if not re.match(r"^\d{1,2}:\d{2}\s+", line):
            continue
        # 09:18 Oslo / 14:20 Myrdal via Train
        place = re.sub(r"^\d{1,2}:\d{2}\s+", "", line)
        place = re.split(r"\s+via\s+|\s+Via\s+", place, maxsplit=1)[0].strip(" -:|,")
        place = _polish_overview_item(place)
        if place and place not in places:
            places.append(place)
    return places

def _line_with_time(label, row):
    time = display_time(row.get("time", "")) or _inline_arrival_time(row)
    return f"{label} — {time}" if time else label


def _norway_nutshell_lines(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    if "norway in a nutshell" not in text:
        return []
    places = _extract_timed_route_places(row)
    lines = []
    base = get_travel_sequence_line(row)
    if places and len(places) >= 2:
        lines.append(_line_with_time(f"Scenic Rail & Fjord Journey from {places[0]} to {places[-1]}", row))
        lines.append("Route: " + " → ".join(places))
    elif base:
        lines.append(_line_with_time(base, row))
    includes = polish_inclusion_items([clean_include_item(item, row.get("title", "")) for item in normalize_list(row.get("includes", []))])
    if includes:
        lines.append("Included journey: " + ", ".join(includes))
    return lines

def _inline_arrival_time(row):
    text = f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'
    match = re.search(r"\barrival\s+to\s+[A-Za-zÀ-ÿøØåÅäÄöÖ\s]+\s+at\s+(\d{1,2}:\d{2}\s*(?:am|pm))", text, flags=re.IGNORECASE)
    if match:
        return display_time(match.group(1))
    if get_row_type(row) == "Cruise" and "overnight" in text.lower():
        times = re.findall(r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b", text, flags=re.IGNORECASE)
        if len(times) >= 2:
            return display_time(times[-1])
    return ""

def get_travel_arrangement_line(row):
    title = get_travel_sequence_line(row)
    time = display_time(row.get("time", "")) or _inline_arrival_time(row)
    duration = polish_client_text(row.get("duration", ""))
    details = []

    if time:
        details.append(time)
    arrival_time = _inline_arrival_time(row)
    if arrival_time and arrival_time != time:
        details.append(f"arrives {arrival_time}")
    if get_row_type(row) == "Cruise":
        cabin_match = re.search(r"\b(?:\d+\s*x\s*)?Cabin\s*\(([^)]+)\)", f'{row.get("details", "")} {row.get("original_title", "")}', flags=re.IGNORECASE)
        if cabin_match:
            details.append(f"{polish_title(cabin_match.group(1))} cabin")
    if duration and " - " not in time:
        clean_duration = format_duration_display(duration)
        if clean_duration:
            details.append(clean_duration)

    return f"{title} — {'; '.join(details)}" if details else title

def build_travel_arrangements_block(travel_rows):
    items = []
    for row in travel_rows:
        special_lines = _norway_nutshell_lines(row)
        if special_lines:
            for line in special_lines:
                if line and line not in items:
                    items.append(line)
            continue
        line = get_travel_arrangement_line(row)
        if line and line not in items:
            items.append(line)

    items = polish_inclusion_items(items)
    if not items:
        return None

    html_text = '<div class="content-block travel-sequence-block">'
    html_text += '<div class="section-title">Travel Arrangements</div>'
    html_text += render_list_items(items)
    html_text += "</div>"

    return {
        "kind": "travel_sequence",
        "row_id": "travel-arrangements",
        "html": html_text,
    }

