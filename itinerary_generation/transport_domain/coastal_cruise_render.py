"""Render helpers for coastal cruise transfer travel sequences."""

from __future__ import annotations

import re
from typing import Callable

from itinerary_generation.common import get_row_type
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.render_model import RenderBlock, RenderMetaLine, RenderSection
from itinerary_generation.render_text_helpers import clean_space
from itinerary_generation.route_intelligence import route_profile_for_places, route_profile_for_row
from itinerary_generation.time_display import display_time
from itinerary_generation.transport_domain.titles import get_transport_route_phrase
from itinerary_generation.transport_model import get_transport_source_text
from itinerary_generation.transport_times import get_transport_time_text
from text_polish import polish_inclusion_items, polish_title


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


def build_coastal_cruise_block(
    travel_rows,
    legacy_lines: list[str],
    *,
    travel_sequence_line_func: Callable[[dict], str],
    travel_arrangement_line_func: Callable[[dict], str],
) -> RenderBlock | None:
    """Build a premium structured block for coastal cruise transfer days."""

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
    profile = route_profile_for_row(cruise_row) or route_profile_for_places(origin, destination, "coastal_cruise", get_transport_source_text(cruise_row))

    flow_items: list[str] = []
    for row in travel_rows:
        row_type = get_row_type(row)
        if row is cruise_row:
            cruise_route = f"{origin} → {destination}" if origin and destination and origin.lower() != destination.lower() else (route_phrase or travel_sequence_line_func(row))
            detail = f"{cruise_route} · {time_value}" if time_value else cruise_route
            flow_items.append(f"Coastal cruise — {detail}")
            continue
        if row_type != "Transfer":
            continue
        line = travel_arrangement_line_func(row)
        if row_type == "Transfer":
            line = re.sub(r"^Private transfer\s+", "", line, flags=re.IGNORECASE).strip(" :-")
            if line:
                line = f"Private transfer — {line[:1].upper() + line[1:]}"
        if line and line not in flow_items:
            flow_items.append(line)

    includes = polish_inclusion_items([clean_include_item(item, route_phrase) for item in (cruise_row.get("includes") or [])])
    extra_sections = [RenderSection("Journey sequence", flow_items)]
    if profile and profile.highlights:
        extra_sections.append(RenderSection("Highlights", list(profile.highlights)))
    if includes:
        extra_sections.append(RenderSection("Cruise inclusions", includes[:6]))

    meta = []
    if time_value:
        meta.append(RenderMetaLine("Time", time_value))

    return RenderBlock(
        kind="travel_sequence",
        row_id="travel-arrangements",
        section_title="Travel Arrangements",
        title=profile.title if profile else route_title,
        meta=meta,
        description=(profile.description if profile else (
            "A coordinated coastal transfer day, pairing private port transfers with the scenic cruise leg "
            "as one clear door-to-door arrangement."
        )),
        lines=[],
        extra_sections=extra_sections,
        css_class="travel-sequence-block",
        source_row_ids=[str(row.get("row_id") or "") for row in travel_rows if row.get("row_id")],
    )
