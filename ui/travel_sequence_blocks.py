"""Travel-arrangement sequence block builders."""

from __future__ import annotations

import re

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.content_engine import clean_client_title
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer, get_transport_route_phrase
from itinerary_generation.transport_norway import extract_norway_nutshell_route_points, format_norway_nutshell_route
from itinerary_generation.transport_model import get_transport_source_text, is_transport_like_row
from itinerary_generation.transport_safety import (
    base_destination_from_terminal,
    destination_is_terminal,
    normalize_transport_place,
    split_self_transfer_notes,
)
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
    return is_transport_like_row(row, include_drive=True)


def _drive_route_line(row):
    text = clean_space(get_transport_source_text(row))
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
        title = _clean_self_arranged_travel_title(get_transport_route_phrase(row) or row.get("title", "Self-arranged travel"))
        if row_type == "Flight" and title.lower().startswith("flight"):
            return f"Self-arranged {title[0].lower() + title[1:]} (not included)"
        return f"{title} (self-arranged, not included)"

    if row_type == "Transfer" and is_route_transfer(row):
        text = get_transport_source_text(row).lower()
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
    text = f"{phrase} {get_transport_source_text(row)}"
    # When the only useful extra detail is ticket noise, keep the day line
    # destination-focused. Otherwise preserve route/service quality such as
    # "Panoramic Coach Transfer from Tromsø to Alta".
    if re.search(r"\b(?:coach|bus)\b", text, flags=re.IGNORECASE) and re.search(r"\btickets?\s+included\b", text, flags=re.IGNORECASE):
        match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s*,?\s*via\b|\s*[-—;|,]\s*|$)", phrase, flags=re.IGNORECASE)
        if match:
            destination = normalize_transport_place(match.group(1))
            if destination_is_terminal(destination):
                return phrase
            destination = polish_title(base_destination_from_terminal(destination) or destination)
            if destination:
                return f"Coach Transfer to {destination}"
    return phrase

def _clean_self_arranged_travel_title(title):
    text = polish_title(strip_price_fragments(str(title or "")))
    text = re.sub(r"\s*,?\s*(?:cost|price)\s*not\s*included\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,?\s*self[-\s]*(?:arranged|arrnaged|arrnage)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,-:|")
    return polish_title(text)


def _split_time_range(value: str) -> tuple[str, str]:
    text = clean_space(value)
    match = re.match(r"^(?P<dep>.+?)\s+-\s+(?P<arr>.+)$", text)
    if not match:
        return "", ""
    return clean_space(match.group("dep")), clean_space(match.group("arr"))


def _coach_terminal_transfer_lines(row):
    text = get_transport_source_text(row)
    if not re.search(r"\b(?:coach|bus)\b", text, flags=re.IGNORECASE):
        return []
    phrase = get_transport_route_phrase(row)
    if not phrase:
        return []
    # Use this expanded shape only when terminals/admin wording make a single
    # long bullet likely to look messy. Simple resort coach transfers keep the
    # existing compact line to avoid changing good output.
    if not re.search(r"bus\s*station|bustation|bus\s*terminal|final voucher|relased|released", text, flags=re.IGNORECASE):
        return []
    lines = [phrase]
    time_text = display_time(get_transport_time_text(row))
    dep, arr = _split_time_range(time_text)
    if dep and arr:
        lines.append(f"Departure: {dep}")
        lines.append(f"Arrival: {arr}")
    elif time_text:
        lines.append(f"Time: {time_text}")
    duration = format_duration_display(row.get("duration", "")) if row.get("duration") else ""
    duration_match = re.search(r"\b(\d+)\s*h(?:ours?)?\s*(\d+)\s*m(?:in(?:utes?)?)?\b", text, flags=re.IGNORECASE)
    if duration_match:
        duration = f"{int(duration_match.group(1))} hours {int(duration_match.group(2))} minutes"
    if duration:
        lines.append(f"Duration: {duration}")
    if re.search(r"final\s+(?:timing|time)|voucher|relased|released", text, flags=re.IGNORECASE):
        lines.append("Final timing will be confirmed in the travel documents.")
    return lines


def _self_transfer_lines(row):
    if get_row_type(row) != "Transfer" or not is_self_arranged(row):
        return []
    text = get_transport_source_text(row)
    return split_self_transfer_notes(text)

def _extract_timed_route_places(row):
    text = str(row.get("details") or row.get("original_title") or row.get("title") or "")
    return extract_norway_nutshell_route_points(text)

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
    if places and len(places) >= 3:
        lines.append(_line_with_time(f"Scenic Rail & Fjord Journey from {places[0]} to {places[-1]}", row))
        route_text = format_norway_nutshell_route(places)
        if route_text:
            lines.append(f"Route highlights: {route_text}")
    elif base:
        lines.append(_line_with_time(base, row))
    includes = polish_inclusion_items([clean_include_item(item, row.get("title", "")) for item in normalize_list(row.get("includes", []))])
    if includes:
        lines.append("Included journey: " + ", ".join(includes))
    return lines

def _santa_claus_express_lines(row):
    text = f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'.lower()
    if "santa claus express" not in text:
        return []
    title = get_travel_sequence_line(row)
    details = get_transport_detail_items(row, title)
    lines = [title] if title else []
    schedule = display_time(get_transport_time_text(row))
    if schedule and schedule not in lines:
        lines.append(schedule)
    for detail in details:
        clean_detail = clean_space(detail)
        if not clean_detail:
            continue
        if re.search(r"\bcabin\b", clean_detail, flags=re.IGNORECASE) and not clean_detail.lower().startswith("cabin"):
            clean_detail = f"Cabin: {clean_detail}"
        if clean_detail not in lines:
            lines.append(clean_detail)
    return lines

def _inline_arrival_time(row):
    text = get_transport_source_text(row)
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
        special_lines = _self_transfer_lines(row) or _norway_nutshell_lines(row) or _santa_claus_express_lines(row) or _coach_terminal_transfer_lines(row)
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

