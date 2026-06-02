"""Travel-arrangement sequence block builders."""

from __future__ import annotations

import re

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.content_engine import clean_client_title
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer, get_transport_route_phrase
from itinerary_generation.transport_details import get_transport_detail_items
from itinerary_generation.transport_times import get_transport_time_text
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
    return get_transport_route_phrase(row)

def is_travel_sequence_candidate(row):
    """Rows that form chronological travel arrangements within a day.

    Self-drive ``Drive`` rows are route guidance, not inclusions. Treating them
    as travel-sequence rows keeps them out of generic ``Included Today`` blocks
    and lets preview/PDF render them consistently as driving routes.
    """

    row_type = get_row_type(row)
    if _is_cruise_leisure_row(row):
        return False
    return row_type == "Transfer" or row_type == "Drive" or row_type in TRANSPORT_TYPES


def _drive_route_line(row):
    text = clean_space(" ".join(str(row.get(key, "") or "") for key in ["title", "details", "original_title"]))
    origin = polish_title(clean_space(row.get("city", "")))
    destination = ""
    match = re.search(r"\bdrive\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+-|\s+time\s*:|\s*\(|$)", text, flags=re.IGNORECASE)
    if match:
        destination = polish_title(clean_space(match.group(1)).strip(" .:-"))
    if origin and destination and origin.lower() != destination.lower():
        label = f"{origin} to {destination}"
    elif destination:
        label = f"Drive to {destination}"
    else:
        label = polish_title(re.sub(r"\s*-\s*\d.*$", "", text).strip(" -:|")) or "Self-drive route"

    time = display_time(row.get("time", ""))
    if not time:
        time_match = re.search(r"(?:time\s*:\s*)?(\d{1,2}:\d{2}\s*(?:am|pm)\s*[-–—]+\s*\d{1,2}:\d{2}\s*(?:am|pm)?)", text, flags=re.IGNORECASE)
        if time_match:
            time = display_time(time_match.group(1))
    duration = clean_space(row.get("duration", ""))
    if not duration:
        duration_match = re.search(r"\b(\d+\s*(?:minutes?|hours?|hrs?))\b", text, flags=re.IGNORECASE)
        if duration_match:
            duration = format_duration_display(duration_match.group(1))
    details = []
    if time:
        details.append(time)
    elif duration:
        details.append(duration)
    return f"{label} — {'; '.join(details)}" if details else label

def get_travel_sequence_line(row):
    row_type = get_row_type(row)

    if row_type == "Drive":
        return _drive_route_line(row)

    if row_type == "Transfer" and is_self_arranged(row):
        title = _clean_self_arranged_travel_title(get_transfer_travel_title(row) or row.get("title", "Self-arranged travel"))
        return f"{title} (self-arranged, not included)"

    if row_type in TRANSPORT_TYPES and is_self_arranged(row):
        title = _clean_self_arranged_travel_title(row.get("title", "Self-arranged travel"))
        if row_type == "Flight" and title.lower().startswith("flight"):
            return f"Self-arranged {title[0].lower() + title[1:]} (not included)"
        return f"{title} (self-arranged, not included)"

    if row_type == "Transfer" and is_route_transfer(row):
        text = f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'.lower()
        if any(marker in text for marker in ["train", "ferry", "cruise", "flight"]):
            return get_transport_route_phrase(row) or get_transfer_travel_title(row) or polish_title(row.get("title", ""))
        return get_transfer_travel_title(row) or polish_title(row.get("title", ""))

    if row_type == "Transfer":
        return clean_client_title(row.get("title", ""), row)

    if row_type in TRANSPORT_TYPES:
        phrase = get_transport_route_phrase(row)
        if phrase:
            return _destination_focused_coach_day_line(row, phrase)
        return polish_title(row.get("title", ""))

    return polish_title(row.get("title", ""))


def _destination_focused_coach_day_line(row, phrase):
    text = f'{phrase} {row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'
    if "norway in a nutshell" in text.lower():
        return phrase
    if not re.search(r"\b(?:coach|bus)\b", text, flags=re.IGNORECASE):
        return phrase
    match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s*,?\s*via\b|\s*[-—;|,]\s*|$)", phrase, flags=re.IGNORECASE)
    if match:
        destination = polish_title(clean_space(match.group(1)).strip(" .:-"))
        destination = re.sub(r"\bbus\s+Station\b", "Bus Station", destination, flags=re.IGNORECASE)
        if destination:
            return f"Coach Transfer to {destination}"
    return phrase

def _clean_self_arranged_travel_title(title):
    text = polish_title(strip_price_fragments(str(title or "")))
    text = re.sub(r"\s*,?\s*(?:cost|price)\s*not\s*included\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,?\s*self[-\s]*(?:arranged|arrnaged|arrnage)\b", "", text, flags=re.IGNORECASE)
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
    time = display_time(get_transport_time_text(row)) or _inline_arrival_time(row)
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
        destination_match = re.search(r"\bNorway in a Nutshell from [^—]+ to ([A-Za-zÀ-ÿøØåÅäÄöÖ ]+)\b", base)
        if destination_match:
            base = f"Norway in a Nutshell to {polish_title(destination_match.group(1).strip())}"
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
    if get_row_type(row) == "Drive":
        return _drive_route_line(row)

    title = get_travel_sequence_line(row)
    time = display_time(get_transport_time_text(row)) or _inline_arrival_time(row)
    duration = polish_client_text(row.get("duration", ""))
    details = []

    if time:
        details.append(time)
    arrival_time = _inline_arrival_time(row)
    if arrival_time and arrival_time != time:
        details.append(f"arrives {arrival_time}")
    if get_row_type(row) == "Cruise":
        cabin_match = re.search(r"\b(?:\d+\s*x\s*)?Cabin\s*\(([^)]+)\)", f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}', flags=re.IGNORECASE)
        if cabin_match:
            details.append(f"{polish_title(cabin_match.group(1))} cabin")
    for detail_item in get_transport_detail_items(row, title):
        detail_lower = detail_item.lower()
        # Day travel lines should not repeat ordinary coach/train ticket notes;
        # commercial ticket detail belongs on the final inclusions page. Keep
        # meaningful operational details such as sleeper cabins, rail seats and
        # ferry car tickets.
        if detail_lower in {"coach ticket included", "train ticket included", "ticket included"}:
            continue
        if detail_item and detail_lower not in title.lower() and detail_item not in details:
            details.append(detail_item)
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

    section_title = "Self-drive route" if all(get_row_type(row) == "Drive" for row in travel_rows) else "Travel Arrangements"
    html_text = '<div class="content-block travel-sequence-block">'
    html_text += f'<div class="section-title">{section_title}</div>'
    html_text += render_list_items(items)
    html_text += "</div>"

    return {
        "kind": "travel_sequence",
        "row_id": "travel-arrangements",
        "html": html_text,
    }

