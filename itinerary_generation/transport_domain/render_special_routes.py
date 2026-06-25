"""Render special transport routes and self-transfer instructions."""

import re

from shared.commercial_markers import has_self_transfer_marker
from itinerary_generation.common import get_row_type
from itinerary_generation.render_text_helpers import clean_space
from itinerary_generation.time_display import display_time
from itinerary_generation.transport_details import get_transport_detail_items
from itinerary_generation.transport_domain.titles import get_transport_route_phrase
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_safety import split_self_transfer_notes
from itinerary_generation.transport_times import get_transport_time_text
from text_polish import format_duration_display


def inline_arrival_time(row):
    text = get_transport_source_text(row)
    match = re.search(r"\barrival\s+to\s+[A-Za-zÀ-ÿøØåÅäÄöÖ\s]+\s+at\s+(\d{1,2}:\d{2}\s*(?:am|pm))", text, flags=re.IGNORECASE)
    if match: return display_time(match.group(1))
    if get_row_type(row) == "Cruise" and "overnight" in text.lower():
        times = re.findall(r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b", text, flags=re.IGNORECASE)
        if len(times) >= 2: return display_time(times[-1])
    return ""


def coach_terminal_transfer_lines(row):
    text, phrase = get_transport_source_text(row), get_transport_route_phrase(row)
    if not re.search(r"\b(?:coach|bus)\b", text, flags=re.IGNORECASE) or not phrase: return []
    if not re.search(r"bus\s*station|bustation|bus\s*terminal|final voucher|relased|released", text, flags=re.IGNORECASE): return []
    lines = [phrase]; time_text = display_time(get_transport_time_text(row))
    match = re.match(r"^(?P<dep>.+?)\s+-\s+(?P<arr>.+)$", clean_space(time_text))
    if match: lines.extend((f"Departure: {clean_space(match.group('dep'))}", f"Arrival: {clean_space(match.group('arr'))}"))
    elif time_text: lines.append(f"Time: {time_text}")
    duration = format_duration_display(row.get("duration", "")) if row.get("duration") else ""
    match = re.search(r"\b(\d+)\s*h(?:ours?)?\s*(\d+)\s*m(?:in(?:utes?)?)?\b", text, flags=re.IGNORECASE)
    if match: duration = f"{int(match.group(1))} hours {int(match.group(2))} minutes"
    if duration: lines.append(f"Duration: {duration}")
    if re.search(r"final\s+(?:timing|time)|voucher|relased|released", text, flags=re.IGNORECASE): lines.append("Final timing will be confirmed in the travel documents.")
    return lines


def self_transfer_lines(row):
    title, details, original = (clean_space(row.get(key, "")) for key in ("title", "details", "original_title"))
    if title and has_self_transfer_marker(title): source = title
    elif details and has_self_transfer_marker(details): source = details
    elif original and has_self_transfer_marker(original): source = original
    else: source = get_transport_source_text(row)
    if details and details.lower() != source.lower() and any(marker in details.lower() for marker in ("private transfer may", "additional cost", "addon cost", "add-on cost", "paid on ground")) and details.lower() not in source.lower(): source = f"{source}. {details}"
    if not has_self_transfer_marker(source.lower()): return []
    notes, city = split_self_transfer_notes(clean_space(source)), clean_space(row.get("city", ""))
    return [re.sub(rf"^{re.escape(city)}\s*:\s*", "", note, flags=re.IGNORECASE).strip() for note in notes] if city else notes


def santa_claus_express_lines(row):
    text = f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'.lower()
    if "santa claus express" not in text: return []
    from itinerary_generation.transport_domain.render_sequences import get_travel_sequence_line
    title = get_travel_sequence_line(row); lines = [title] if title else []
    schedule = display_time(get_transport_time_text(row))
    if schedule and schedule not in lines: lines.append(schedule)
    for detail in get_transport_detail_items(row, title):
        detail = clean_space(detail)
        if re.search(r"\bcabin\b", detail, flags=re.IGNORECASE) and not detail.lower().startswith("cabin"): detail = f"Cabin: {detail}"
        if detail and detail not in lines: lines.append(detail)
    return lines
