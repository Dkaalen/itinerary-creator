"""Build canonical one-line labels for travel-sequence rows."""

import re

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged
from itinerary_generation.content_engine import clean_client_title
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.render_text_helpers import clean_space
from itinerary_generation.time_display import display_time
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_domain.titles import get_transfer_travel_title, get_transport_route_phrase
from itinerary_generation.transport_model import get_transport_source_text, is_transport_like_row
from itinerary_generation.transport_render_blocks import is_cruise_leisure_row
from itinerary_generation.transport_safety import base_destination_from_terminal, destination_is_terminal, normalize_transport_place
from text_polish import format_duration_display, polish_title, strip_price_fragments


def is_travel_sequence_candidate(row):
    return not is_cruise_leisure_row(row) and is_transport_like_row(row, include_drive=True)


def drive_route_line(row):
    text, origin = clean_space(get_transport_source_text(row)), polish_title(clean_space(row.get("city", "")))
    match = re.search(r"\bdrive\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+-|\s+time\s*:|\s*\(|$)", text, flags=re.IGNORECASE)
    destination = polish_title(clean_space(match.group(1)).strip(" .:-")) if match else ""
    if origin and destination and origin.lower() != destination.lower(): label = f"{origin} to {destination}"
    elif destination: label = f"Drive to {destination}"
    else: label = polish_title(re.sub(r"\s*[-–—]\s*\d.*$", "", text).strip(" -:|")) or "Self-drive route"
    time = display_time(row.get("time", ""))
    if not time:
        found = re.search(r"(?:time\s*:\s*)?(\d{1,2}:\d{2}\s*(?:am|pm)\s*[-–—]+\s*\d{1,2}:\d{2}\s*(?:am|pm)?)", text, flags=re.IGNORECASE)
        if found: time = display_time(found.group(1))
    duration = clean_space(row.get("duration", ""))
    if not duration:
        found = re.search(r"\b(\d+\s*(?:minutes?|hours?|hrs?))\b", text, flags=re.IGNORECASE)
        if found: duration = format_duration_display(found.group(1))
    detail = time or duration
    return f"{label} — {detail}" if detail else label


def _clean_self_arranged_title(title):
    text = polish_title(strip_price_fragments(str(title or "")))
    text = re.sub(r"\s*,?\s*(?:cost|price)\s*not\s*included\b|\s*,?\s*self[-\s]*(?:arranged|arrnaged|arrnage)\b", "", text, flags=re.IGNORECASE)
    return polish_title(re.sub(r"\s{2,}", " ", text).strip(" ,-:|"))


def _destination_focused_coach_line(row, phrase):
    text = f"{phrase} {get_transport_source_text(row)}"
    if re.search(r"\b(?:coach|bus)\b", text, flags=re.IGNORECASE) and re.search(r"\btickets?\s+included\b", text, flags=re.IGNORECASE):
        match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s*,?\s*via\b|\s*[-—;|,]\s*|$)", phrase, flags=re.IGNORECASE)
        if match:
            destination = normalize_transport_place(match.group(1))
            if destination_is_terminal(destination): return f"Coach Transfer to {destination}"
            destination = polish_title(base_destination_from_terminal(destination) or destination)
            if destination: return f"Coach Transfer to {destination}"
    return phrase


def get_travel_sequence_line(row):
    row_type = get_row_type(row)
    if row_type == "Drive": return drive_route_line(row)
    if row_type == "Transfer" and is_self_arranged(row):
        return f"{_clean_self_arranged_title(get_transfer_travel_title(row) or row.get('title', 'Self-arranged travel'))} (self-arranged, not included)"
    if row_type in TRANSPORT_TYPES and is_self_arranged(row):
        title = _clean_self_arranged_title(get_transport_route_phrase(row) or row.get("title", "Self-arranged travel"))
        if row_type == "Flight" and title.lower().startswith("flight"):
            match = re.search(r"\bflight\s+from\s+.+?\s+to\s+(.+)$", title, flags=re.IGNORECASE)
            if match and polish_title(match.group(1).strip(" -:|.,")): title = f"Flight to {polish_title(match.group(1).strip(' -:|.,'))}"
            return f"Self-arranged {title[0].lower() + title[1:]} (not included)"
        return f"{title} (self-arranged, not included)"
    if row_type == "Transfer" and is_route_transfer(row):
        text = get_transport_source_text(row).lower()
        phrase = get_transport_route_phrase(row) or get_transfer_travel_title(row) or polish_title(row.get("title", ""))
        return _destination_focused_coach_line(row, phrase) if any(marker in text for marker in ("train", "ferry", "cruise", "flight", "coach", "bus")) else get_transfer_travel_title(row) or polish_title(row.get("title", ""))
    if row_type == "Transfer": return clean_client_title(row.get("title", ""), row) or polish_title(row.get("title", ""))
    if row_type in TRANSPORT_TYPES:
        journey = resolve_nutshell_journey(row)
        if journey is not None: return journey.client_title
        phrase = get_transport_route_phrase(row)
        return _destination_focused_coach_line(row, phrase) if phrase else polish_title(row.get("title", ""))
    return polish_title(row.get("title", ""))
