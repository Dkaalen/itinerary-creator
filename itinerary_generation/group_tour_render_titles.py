"""Build group-tour day titles, destinations and introductory copy."""

import re
from typing import Any, Iterable, Mapping

from itinerary_generation.group_tour_render_context import group_tour_day_from_rows, group_tour_package_context_from_rows
from itinerary_generation.group_tour_render_utils import clean
from itinerary_generation.time_display import display_time
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title

REYKJAVIK_KEYS = {"reykjavik", "reykjavík"}
TITLE_REPLACEMENTS = ((r"\bgolden circle\b", "Golden Circle"), (r"\bsouth coast\b", "South Coast"), (r"\bnorth iceland\b", "North Iceland"), (r"\bwest iceland\b", "West Iceland"), (r"\beast fjords?\b|\beastfjords\b", "East Fjords"), (r"\bglacier lagoon\b", "Glacier Lagoon"), (r"\bdiamond beach\b", "Diamond Beach"), (r"\bblack sand beach\b", "Black Sand Beach"), (r"\bice cave\b", "Ice Cave"))


def group_tour_day_title(rows: Iterable[Mapping[str, Any]]) -> str:
    segment = group_tour_day_from_rows(rows)
    if segment is None: return ""
    title = polish_title(segment.title)
    for pattern, replacement in TITLE_REPLACEMENTS: title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    return title[:1].upper() + title[1:] if title else "Guided group tour"


def group_tour_day_city(rows: Iterable[Mapping[str, Any]]) -> str:
    row_list = list(rows or ()); segment = group_tour_day_from_rows(row_list)
    if segment is not None:
        if segment.overnight_area: return polish_title(canonicalize_place_name(segment.overnight_area))
        route = [canonicalize_place_name(place) for place in segment.route if clean(place)]
        non_capital = [place for place in route if place.casefold() not in REYKJAVIK_KEYS]
        if non_capital: return polish_title(non_capital[-1])
        if route: return polish_title(route[-1])
    for row in row_list:
        city = canonicalize_place_name(row.get("city", ""))
        if city and not re.fullmatch(r"Day\s*\d+", city, flags=re.IGNORECASE): return polish_title(city)
    return "Iceland"


def group_tour_day_intro(rows: Iterable[Mapping[str, Any]]) -> str:
    row_list = list(rows or ()); segment = group_tour_day_from_rows(row_list)
    if segment is None: return ""
    context = group_tour_package_context_from_rows(row_list); duration = int(context.get("duration_days") or 0); season = clean(context.get("season")); title = group_tour_day_title(row_list)
    if segment.package_day_number == 1:
        lead = "Your guided group tour begins today" + (f" on this {duration}-day programme" if duration else "")
        logistics = []; pickup = display_time(context.get("pickup_time", "")) or clean(context.get("pickup_time")); meeting = clean(context.get("meeting_point"))
        if pickup: logistics.append(f"pick-up {pickup[:1].lower() + pickup[1:]}" if pickup.casefold().startswith("between ") else f"pick-up at {pickup}")
        if meeting: logistics.append(f"from {meeting}")
        return polish_client_text(f"{lead}{' with ' + ' '.join(logistics) if logistics else ''}. The first{f' {season}' if season in {'summer', 'winter'} else ''} programme day focuses on {title}.")
    if duration and segment.package_day_number == duration: return polish_client_text(f"Complete your guided group tour with {title}, following the final planned route and conditions shown below.")
    return polish_client_text(f"{title} is the focus of today’s guided programme, following the planned route and arrangements for this stage of the journey.")
