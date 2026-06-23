"""Canonical travel-arrangement sequence builders."""

from __future__ import annotations

import re

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged
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
from itinerary_generation.transport_norway import format_norway_nutshell_route
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


def _self_transfer_lines(row):
    text = get_transport_source_text(row)
    lower = text.lower()
    if "self transfer" not in lower and "self-arranged transfer" not in lower:
        return []
    return split_self_transfer_notes(text)


def _line_with_time_value(label: str, time_value: str, row: dict) -> str:
    time = display_time(time_value) or display_time(get_transport_time_text(row)) or _inline_arrival_time(row)
    return f"{label} — {time}" if time else label


def _nutshell_leg_line(leg) -> str:
    origin = clean_space(leg.origin)
    destination = clean_space(leg.destination)
    if not origin or not destination:
        return ""
    departure = display_time(leg.departure_time)
    arrival = display_time(leg.arrival_time)
    if departure and arrival:
        line = f"{departure} {origin} - {arrival} {destination}"
    elif departure:
        line = f"{departure} {origin} - {destination}"
    elif arrival:
        line = f"{origin} - {arrival} {destination}"
    else:
        line = f"{origin} to {destination}"
    return f"{line} — {leg.mode}" if leg.mode else line


def _norway_nutshell_lines(row):
    journey = resolve_nutshell_journey(row)
    if journey is None:
        return []

    lines = [_line_with_time_value(journey.client_title, journey.journey_time, row)]
    timed_legs = [leg for leg in journey.legs if leg.departure_time or leg.arrival_time]
    if timed_legs and not journey.warnings:
        lines.extend(line for line in (_nutshell_leg_line(leg) for leg in timed_legs) if line)
    elif len(journey.route_points) >= 3 and not journey.warnings:
        route_text = format_norway_nutshell_route(list(journey.route_points))
        if route_text:
            lines.append(f"Route highlights: {route_text}")

    supplier_route_items = polish_inclusion_items(list(journey.supplier_includes))
    if supplier_route_items:
        first, *rest = supplier_route_items
        lines.append(f"Included journey: {first}")
        lines.extend(rest)
    else:
        includes = polish_inclusion_items(
            [clean_include_item(item, journey.client_title) for item in journey.included_services]
        )
        if includes:
            lines.append("Included journey: " + ", ".join(includes))
    return list(dict.fromkeys(line for line in lines if line))


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



def _travel_row_lines(row) -> list[str]:
    special_lines = _self_transfer_lines(row) or _norway_nutshell_lines(row) or _santa_claus_express_lines(row) or _coach_terminal_transfer_lines(row)
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


def _route_arrow_text(points: list[str] | tuple[str, ...]) -> str:
    clean_points = [polish_title(clean_space(point)) for point in points or [] if clean_space(point)]
    return " → ".join(dict.fromkeys(clean_points))


def _timed_leg_label(leg) -> str:
    line = _nutshell_leg_line(leg)
    return line.replace(" - ", " → ", 1) if line else ""


def _build_featured_nutshell_block(travel_rows, legacy_lines: list[str]) -> RenderBlock | None:
    nutshell_row = None
    journey = None
    for row in travel_rows:
        journey = resolve_nutshell_journey(row)
        if journey is not None:
            nutshell_row = row
            break
    if journey is None or nutshell_row is None:
        return None

    time_value = display_time(journey.journey_time) or display_time(get_transport_time_text(nutshell_row))
    transfer_lines: list[str] = []
    for row in travel_rows:
        if row is nutshell_row:
            continue
        for line in _travel_row_lines(row):
            if line and line not in transfer_lines:
                transfer_lines.append(line)

    route_points = list(journey.route_points or [])
    if len(route_points) < 3:
        fallback_points: list[str] = []
        route_source_lines = list(journey.supplier_includes or []) + legacy_lines
        route_pattern = re.compile(
            r"\b(?:train(?:\s+transfer)?|coach(?:\s+transfer)?|bus(?:\s+transfer)?|"
            r"fjord\s+cruise|cruise|transfer)\s+"
            r"([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+"
            r"([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s*\(|,|$)",
            flags=re.IGNORECASE,
        )
        for line in route_source_lines:
            for origin, destination in route_pattern.findall(line):
                for point in (origin, destination):
                    clean_point = polish_title(clean_space(point).strip(" -:|.,"))
                    if clean_point and (not fallback_points or fallback_points[-1].lower() != clean_point.lower()):
                        fallback_points.append(clean_point)
        if len(fallback_points) >= 3:
            route_points = fallback_points

    route_text = _route_arrow_text(route_points)
    leg_lines = [_timed_leg_label(leg) for leg in journey.legs if leg.departure_time or leg.arrival_time]
    leg_lines = [line for line in leg_lines if line]
    if not leg_lines and route_text:
        leg_lines = [route_text]

    highlights = []
    combined_route = " ".join(route_points).lower()
    if "bergen" in combined_route:
        highlights.append("Bergen Railway")
    if "flåm" in combined_route or "flam" in combined_route:
        highlights.append("Flåm Railway")
    if "gudvangen" in combined_route or "nærøyfjord" in combined_route or "naeroyfjord" in combined_route:
        highlights.append("Nærøyfjord cruise")
    if not highlights:
        highlights = ["Scenic rail", "Fjord landscape", "Self-guided route"]

    supplier_items = polish_inclusion_items(list(journey.supplier_includes or []))
    extra_sections: list[RenderSection] = []
    if route_text:
        extra_sections.append(RenderSection("Route", [route_text]))
    if leg_lines:
        extra_sections.append(RenderSection("Journey timeline", leg_lines))
    if highlights:
        extra_sections.append(RenderSection("Highlights", highlights))
    if supplier_items:
        extra_sections.append(RenderSection("Included journey", supplier_items[:6]))
    if transfer_lines:
        extra_sections.append(RenderSection("Linked transfers", transfer_lines))

    meta = []
    if time_value:
        meta.append(RenderMetaLine("Time", time_value))
    meta.append(RenderMetaLine("Style", "Self-guided scenic journey"))

    return RenderBlock(
        kind="travel_sequence",
        row_id="travel-arrangements",
        section_title="Featured Scenic Journey",
        title=journey.client_title,
        meta=meta,
        description=(
            "A signature Norway rail-and-fjord journey, combining mountain railway scenery, "
            "fjord villages and scheduled connections in one carefully sequenced route."
        ),
        lines=legacy_lines,
        extra_sections=extra_sections,
        css_class="travel-sequence-block premium-travel-card featured-journey-block",
        source_row_ids=[str(row.get("row_id") or "") for row in travel_rows if row.get("row_id")],
    )


def _transport_place_from_title(text: str, fallback: str = "") -> str:
    match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:\s+-|\s+time\s*:|\s+meeting\s+point\s*:|\s+includes?\s*:|$)", text, flags=re.IGNORECASE)
    if match:
        return polish_title(clean_space(match.group(1)).strip(" -:|.,"))
    return polish_title(clean_space(fallback))


def _is_coastal_transfer_cruise_row(row) -> bool:
    if get_row_type(row) != "Cruise":
        return False
    text = get_transport_source_text(row)
    return bool(re.search(r"\bcoastal\b|\bcruise\s+transfer\b|\batlantic\s+coastal\b", text, flags=re.IGNORECASE))


def _build_coastal_cruise_block(travel_rows, legacy_lines: list[str]) -> RenderBlock | None:
    cruise_row = next((row for row in travel_rows if _is_coastal_transfer_cruise_row(row)), None)
    if cruise_row is None:
        return None

    source_title = polish_title(cruise_row.get("title", ""))
    detected_phrase = get_transport_route_phrase(cruise_row)
    if source_title and re.search(r"\bcoastal\b.*\bcruise\b.*\btransfer\b|\bcruise\s+transfer\b", source_title, flags=re.IGNORECASE):
        route_phrase = source_title
    else:
        route_phrase = detected_phrase or source_title
    origin = polish_title(clean_space(cruise_row.get("city", "")))
    destination = _transport_place_from_title(route_phrase or get_transport_source_text(cruise_row), "")
    route_title = f"{origin} → {destination}" if origin and destination and origin.lower() != destination.lower() else route_phrase or "Coastal Cruise Transfer"
    time_value = display_time(get_transport_time_text(cruise_row))

    flow_items: list[str] = []
    for row in travel_rows:
        row_type = get_row_type(row)
        if row is cruise_row:
            cruise_label = "Coastal cruise"
            cruise_route = route_phrase or get_travel_sequence_line(row)
            if time_value:
                flow_items.append(f"{cruise_label}: {cruise_route} — {time_value}")
            else:
                flow_items.append(f"{cruise_label}: {cruise_route}")
            continue
        line = get_travel_arrangement_line(row)
        if row_type == "Transfer":
            line = re.sub(r"^Private transfer\s+", "Private transfer: ", line, flags=re.IGNORECASE)
        if line and line not in flow_items:
            flow_items.append(line)

    includes = polish_inclusion_items([clean_include_item(item, route_phrase) for item in (cruise_row.get("includes") or [])])
    extra_sections = [RenderSection("Coordinated day flow", flow_items)]
    if includes:
        extra_sections.append(RenderSection("Cruise inclusions", includes[:6]))

    meta = [RenderMetaLine("Service", "Coastal cruise transfer")]
    if time_value:
        meta.append(RenderMetaLine("Time", time_value))

    return RenderBlock(
        kind="travel_sequence",
        row_id="travel-arrangements",
        section_title="Travel Arrangements",
        title=route_title,
        meta=meta,
        description=(
            "A coordinated coastal transfer day, pairing private port transfers with the scenic cruise leg "
            "so the journey reads as one door-to-door arrangement."
        ),
        lines=legacy_lines,
        extra_sections=extra_sections,
        css_class="travel-sequence-block premium-travel-card coastal-cruise-card",
        source_row_ids=[str(row.get("row_id") or "") for row in travel_rows if row.get("row_id")],
    )

def build_travel_arrangements_render_block(travel_rows):
    items = _legacy_travel_lines(travel_rows)
    if not items:
        return None

    premium_block = _build_featured_nutshell_block(travel_rows, items) or _build_coastal_cruise_block(travel_rows, items)
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
