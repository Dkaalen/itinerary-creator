"""Canonical travel-arrangement sequence builders."""

from __future__ import annotations

import re

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged
from shared.commercial_markers import has_self_transfer_marker
from itinerary_generation.content_engine import clean_client_title
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.render_model import RenderBlock, RenderMetaLine, RenderSection
from itinerary_generation.render_text_helpers import clean_space, normalize_list
from itinerary_generation.time_display import display_time
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_domain.titles import get_transfer_travel_title, get_transport_route_phrase
from itinerary_generation.transport_details import get_transport_detail_items
from itinerary_generation.transport_model import get_transport_source_text, is_transport_like_row
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.transport_domain.coastal_cruise_render import build_coastal_cruise_block
from itinerary_generation.transport_domain.nutshell_render import build_featured_nutshell_block, norway_nutshell_lines
from itinerary_generation.transport_render_blocks import is_cruise_leisure_row
from itinerary_generation.transport_safety import (
    base_destination_from_terminal,
    destination_is_terminal,
    normalize_transport_place,
    split_self_transfer_notes,
)
from itinerary_generation.transport_times import get_transport_time_text
from text_polish import format_duration_display, polish_client_text, polish_inclusion_items, polish_title, strip_price_fragments


def _transport_route_phrase(row):
    return get_transport_route_phrase(row)


def _repair_travel_arrangement_case(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\bbus Station\b", "Bus Station", text)
    text = re.sub(r"\bthe Bus Station\b", "the bus station", text)
    text = re.sub(r"\bthe Railway Station\b", "the railway station", text)
    return text


def is_travel_sequence_candidate(row):
    row_type = get_row_type(row)
    if is_cruise_leisure_row(row):
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
        label = polish_title(re.sub(r"\s*[-–—]\s*\d.*$", "", text).strip(" -:|")) or "Self-drive route"

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


def _clean_self_arranged_travel_title(title):
    text = polish_title(strip_price_fragments(str(title or "")))
    text = re.sub(r"\s*,?\s*(?:cost|price)\s*not\s*included\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,?\s*self[-\s]*(?:arranged|arrnaged|arrnage)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,-:|")
    return polish_title(text)


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
            destination_only = re.search(r"\bflight\s+from\s+.+?\s+to\s+(.+)$", title, flags=re.IGNORECASE)
            if destination_only:
                clean_destination = polish_title(destination_only.group(1).strip(" -:|.,"))
                if clean_destination:
                    title = f"Flight to {clean_destination}"
            return f"Self-arranged {title[0].lower() + title[1:]} (not included)"
        return f"{title} (self-arranged, not included)"

    if row_type == "Transfer" and is_route_transfer(row):
        text = get_transport_source_text(row).lower()
        if any(marker in text for marker in ["train", "ferry", "cruise", "flight"]):
            return get_transport_route_phrase(row) or get_transfer_travel_title(row) or polish_title(row.get("title", ""))
        return get_transfer_travel_title(row) or polish_title(row.get("title", ""))

    if row_type == "Transfer":
        return clean_client_title(row.get("title", ""), row) or polish_title(row.get("title", ""))

    if row_type in TRANSPORT_TYPES:
        nutshell_journey = resolve_nutshell_journey(row)
        if nutshell_journey is not None:
            return nutshell_journey.client_title
        title = polish_title(row.get("title", ""))
        phrase = get_transport_route_phrase(row)
        if phrase:
            return _destination_focused_coach_day_line(row, phrase)
        return title

    return polish_title(row.get("title", ""))


def _destination_focused_coach_day_line(row, phrase):
    text = f"{phrase} {get_transport_source_text(row)}"
    if re.search(r"\b(?:coach|bus)\b", text, flags=re.IGNORECASE) and re.search(r"\btickets?\s+included\b", text, flags=re.IGNORECASE):
        match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s*,?\s*via\b|\s*[-—;|,]\s*|$)", phrase, flags=re.IGNORECASE)
        if match:
            destination = normalize_transport_place(match.group(1))
            if destination_is_terminal(destination):
                return f"Coach Transfer to {destination}"
            destination = polish_title(base_destination_from_terminal(destination) or destination)
            if destination:
                return f"Coach Transfer to {destination}"
    return phrase


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


def _self_transfer_source_text(row) -> str:
    """Return the cleanest source field for self-transfer rows.

    Supplier rows often repeat the same sentence in both title and details
    (for example ``Self transfer to station`` plus ``City: Self transfer to
    station``).  Feeding the combined title+details string into the self-transfer
    cleaner produces duplicated client copy in journey modules.  Prefer the
    title when it already contains the self-transfer instruction, otherwise use
    details as the authoritative supplier sentence.
    """

    title = clean_space(row.get("title", ""))
    details = clean_space(row.get("details", ""))
    original_title = clean_space(row.get("original_title", ""))

    if title and has_self_transfer_marker(title):
        source = title
    elif details and has_self_transfer_marker(details):
        source = details
    elif original_title and has_self_transfer_marker(original_title):
        source = original_title
    else:
        source = get_transport_source_text(row)

    # Preserve occasional add-on/private-transfer notes that only appear in the
    # details field, without duplicating the core transfer instruction.
    source_lower = source.lower()
    if details and details.lower() != source_lower:
        details_lower = details.lower()
        if ("private transfer may" in details_lower or "additional cost" in details_lower) and details_lower not in source_lower:
            source = f"{source}. {details}"
    return clean_space(source)


def _self_transfer_lines(row):
    text = _self_transfer_source_text(row)
    lower = text.lower()
    if not has_self_transfer_marker(lower):
        return []
    notes = split_self_transfer_notes(text)
    city = clean_space(row.get("city", ""))
    if city:
        notes = [re.sub(rf"^{re.escape(city)}\s*:\s*", "", note, flags=re.IGNORECASE).strip() for note in notes]
    return notes


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
        if detail_lower in {"coach ticket included", "train ticket included", "ticket included"}:
            continue
        if detail_item and detail_lower not in title.lower() and detail_item not in details:
            details.append(detail_item)
    if duration and " - " not in time:
        clean_duration = format_duration_display(duration)
        if clean_duration:
            details.append(clean_duration)

    return f"{title} — {'; '.join(details)}" if details else title




def _norway_nutshell_lines(row):
    """Compatibility wrapper for older travel_sequence_blocks imports."""

    return norway_nutshell_lines(row, inline_arrival_time_func=_inline_arrival_time)


def _travel_row_lines(row) -> list[str]:
    special_lines = (
        _self_transfer_lines(row)
        or norway_nutshell_lines(row, inline_arrival_time_func=_inline_arrival_time)
        or _santa_claus_express_lines(row)
        or _coach_terminal_transfer_lines(row)
    )
    if special_lines:
        return [line for line in special_lines if line]
    line = get_travel_arrangement_line(row)
    return [line] if line else []


def _legacy_travel_lines(travel_rows) -> list[str]:
    items: list[str] = []
    for row in travel_rows:
        for line in _travel_row_lines(row):
            if line and line not in items:
                items.append(line)
    return [_repair_travel_arrangement_case(item) for item in polish_inclusion_items(items)]


def build_travel_arrangements_render_block(travel_rows):
    items = _legacy_travel_lines(travel_rows)
    if not items:
        return None

    premium_block = build_featured_nutshell_block(
        travel_rows,
        items,
        travel_row_lines_func=_travel_row_lines,
    ) or build_coastal_cruise_block(
        travel_rows,
        items,
        travel_sequence_line_func=get_travel_sequence_line,
        travel_arrangement_line_func=get_travel_arrangement_line,
    )
    if premium_block is not None:
        return premium_block

    section_title = "Self-drive route" if all(get_row_type(row) == "Drive" for row in travel_rows) else "Travel Arrangements"
    return RenderBlock(
        kind="travel_sequence",
        row_id="travel-arrangements",
        section_title=section_title,
        lines=items,
        css_class="travel-sequence-block",
        source_row_ids=[str(row.get("row_id") or "") for row in travel_rows if row.get("row_id")],
    )
