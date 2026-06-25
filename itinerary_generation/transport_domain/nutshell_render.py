"""Render helpers for Norway in a Nutshell travel sequences."""

from __future__ import annotations

import re
from typing import Callable

from itinerary_generation.common import get_row_type
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.nutshell_parsing import format_norway_nutshell_route
from itinerary_generation.render_model import RenderBlock, RenderMetaLine, RenderSection
from itinerary_generation.render_text_helpers import clean_space
from itinerary_generation.route_intelligence import premium_mode_label, route_profile_for_places
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_times import get_transport_time_text
from itinerary_generation.time_display import display_time
from text_polish import polish_inclusion_items, polish_title


def _line_with_time_value(label: str, time_value: str, row: dict, inline_arrival_time_func: Callable[[dict], str]) -> str:
    time = display_time(time_value) or display_time(get_transport_time_text(row)) or inline_arrival_time_func(row)
    return f"{label} — {time}" if time else label




def _nutshell_mode_label(value: str) -> str:
    text = clean_space(value)
    labels = {
        "train": "Train",
        "scenic train": "Scenic Train",
        "bus": "Bus",
        "scenic bus": "Scenic Bus",
        "coach": "Coach",
        "scenic coach": "Scenic Coach",
        "cruise": "Cruise",
        "scenic cruise": "Scenic Cruise",
        "fjord cruise": "Fjord Cruise",
        "ferry": "Ferry",
    }
    return labels.get(text.lower(), polish_title(text))

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
    label = _nutshell_mode_label(leg.mode) if leg.mode else "Journey leg"
    return f"{line} — {label}"


def norway_nutshell_lines(row, *, inline_arrival_time_func: Callable[[dict], str]) -> list[str]:
    """Return legacy line output for a Nutshell row inside generic travel lists."""

    journey = resolve_nutshell_journey(row)
    if journey is None:
        return []

    lines = [_line_with_time_value(journey.client_title, journey.journey_time, row, inline_arrival_time_func)]
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


def _route_arrow_text(points: list[str] | tuple[str, ...]) -> str:
    clean_points = [polish_title(clean_space(point)) for point in points or [] if clean_space(point)]
    return " → ".join(dict.fromkeys(clean_points))


def _timed_leg_label(leg) -> str:
    return _nutshell_leg_line(leg)


def _normalise_transport_mode(value: str) -> str:
    text = polish_title(clean_space(value))
    if not text:
        return "Journey leg"
    return premium_mode_label(text)


def _timeline_time_display(value: str) -> str:
    time_text = display_time(value)
    if time_text:
        return time_text
    match = re.match(
        r"\s*(\d{1,2}:\d{2}\s*(?:am|pm)?)\s*[-–—]+\s*(\d{1,2}:\d{2}\s*(?:am|pm)?)\s*$",
        str(value or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return clean_space(value)
    start = display_time(match.group(1)) or clean_space(match.group(1))
    end = display_time(match.group(2)) or clean_space(match.group(2))
    return f"{start} - {end}" if start and end else clean_space(value)


def _supplier_leg_timeline_items(items: list[str] | tuple[str, ...]) -> list[str]:
    timeline: list[str] = []
    leg_pattern = re.compile(
        r"^\s*(?P<mode>train\s+transfer|coach\s+transfer|bus\s+transfer|fjord\s+cruise|cruise|train|coach|bus)\s+"
        r"(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+"
        r"(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)"
        r"(?:\s*\((?P<time>[^)]+)\))?\s*$",
        flags=re.IGNORECASE,
    )
    for item in items or []:
        clean_item = polish_title(clean_space(item).strip(" -:|.,"))
        match = leg_pattern.match(clean_item)
        if not match:
            continue
        mode = _normalise_transport_mode(match.group("mode"))
        origin = polish_title(clean_space(match.group("origin")))
        destination = polish_title(clean_space(match.group("destination")))
        if not origin or not destination:
            continue
        route = f"{origin} → {destination}"
        time_value = _timeline_time_display(match.group("time") or "")
        detail = f"{route} · {time_value}" if time_value else route
        line = f"{mode} — {detail}"
        if line not in timeline:
            timeline.append(line)
    return timeline


def build_featured_nutshell_block(
    travel_rows,
    legacy_lines: list[str],
    *,
    travel_row_lines_func: Callable[[dict], list[str]],
) -> RenderBlock | None:
    """Build the premium structured Nutshell render block, when present."""

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
        if row is nutshell_row or get_row_type(row) != "Transfer":
            continue
        for line in travel_row_lines_func(row):
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
    supplier_items = polish_inclusion_items(list(journey.supplier_includes or []))
    supplier_leg_lines = _supplier_leg_timeline_items(supplier_items)
    leg_lines = list(supplier_leg_lines)
    if not leg_lines:
        leg_lines = [_timed_leg_label(leg) for leg in journey.legs if leg.departure_time or leg.arrival_time]
        leg_lines = [line for line in leg_lines if line]
    if not leg_lines and route_text:
        leg_lines = [route_text]

    profile = route_profile_for_places(
        journey.origin or (route_points[0] if route_points else ""),
        journey.destination or (route_points[-1] if route_points else ""),
        "norway_in_a_nutshell",
        get_transport_source_text(nutshell_row),
    )
    highlights = list(profile.highlights) if profile else []
    combined_route = " ".join(route_points).lower()
    if not highlights:
        if "bergen" in combined_route:
            highlights.append("Bergen Railway")
        if "flåm" in combined_route or "flam" in combined_route:
            highlights.append("Flåm Railway")
        if "gudvangen" in combined_route or "nærøyfjord" in combined_route or "naeroyfjord" in combined_route:
            highlights.append("Nærøyfjord cruise")
    if not highlights:
        highlights = ["Scenic rail", "Fjord landscape", "Self-guided route"]

    extra_sections: list[RenderSection] = []
    if route_text:
        extra_sections.append(RenderSection("Route", [route_text]))
    if leg_lines:
        extra_sections.append(RenderSection("Journey timeline", leg_lines))
    if highlights:
        extra_sections.append(RenderSection("Highlights", highlights))
    if supplier_items:
        included_items = ["Scheduled rail, coach and fjord-cruise tickets as listed"] if supplier_leg_lines else supplier_items
        extra_sections.append(RenderSection("Included journey", included_items))
    if transfer_lines:
        extra_sections.append(RenderSection("Linked transfers", transfer_lines))

    meta = []
    if time_value:
        meta.append(RenderMetaLine("Time", time_value))

    return RenderBlock(
        kind="travel_sequence",
        row_id="travel-arrangements",
        section_title="Featured Scenic Journey",
        title=journey.client_title or (profile.title if profile else "Norway in a Nutshell"),
        meta=meta,
        description=(
            f"Travel Arrangements: {profile.description}"
            if profile
            else (
                "Travel Arrangements: A signature Norway rail-and-fjord journey, combining "
                "mountain railway scenery, fjord villages and scheduled connections in one carefully sequenced route."
            )
        ),
        lines=[],
        extra_sections=extra_sections,
        css_class="travel-sequence-block",
        source_row_ids=[str(row.get("row_id") or "") for row in travel_rows if row.get("row_id")],
    )
