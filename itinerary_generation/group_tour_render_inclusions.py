"""Build package route and structured inclusion summaries."""

import re
from typing import Any, Mapping

from itinerary_generation.group_tour_domain import GroupTourAccommodationPolicy, GroupTourPackage
from itinerary_generation.group_tour_render_utils import clean, natural_join, unique
from itinerary_generation.structured_model import StructuredListItem
from itinerary_generation.time_display import display_time
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text


def group_tour_package_route(package: GroupTourPackage | None) -> list[str]:
    route = []
    for segment in package.day_segments if package else ():
        for place in segment.route:
            canonical = canonicalize_place_name(place)
            if canonical and (not route or canonical != route[-1]): route.append(canonical)
    return route


def _accommodation_line(policy: GroupTourAccommodationPolicy) -> str:
    if not policy.included: return ""
    parts = [f"{policy.nights} included night{'s' if policy.nights != 1 else ''}" if policy.nights else "Included accommodation during the tour"]
    parts.extend(value for value in (policy.room_basis, policy.bathroom, policy.meal_plan) if value)
    text = ", ".join(parts).rstrip(".") + "."
    if not policy.exact_properties_confirmed: text += " Properties may vary according to availability."
    return polish_client_text(text)


def _programme_values(package: GroupTourPackage) -> list[str]:
    excluded = re.compile(r"\b(hotel|guesthouse|accommodation|private bathroom|breakfast|arrival|pick[-‑ ]?up|drop[- ]?off|minibus|vehicle|guide|wifi)\b", re.IGNORECASE)
    values = []
    for item in package.package_inclusions:
        numbered = bool(re.match(r"^Day\s*\d+", item, flags=re.IGNORECASE)); cleaned = re.sub(r"^and\s+", "", re.sub(r"^Day\s*\d+(?:\s*-\s*\d+)?\s*:\s*", "", item, flags=re.IGNORECASE), flags=re.IGNORECASE)
        if not numbered and not excluded.search(cleaned): values.append(cleaned)
    values.extend(item for segment in package.day_segments for item in segment.included_activities)
    for item in package.package_inclusions:
        if re.match(r"^Day\s*\d+", item, flags=re.IGNORECASE):
            cleaned = re.sub(r"^Day\s*\d+(?:\s*-\s*\d+)?\s*:\s*", "", item, flags=re.IGNORECASE)
            if not excluded.search(cleaned): values.append(cleaned)
    return unique(values)


def group_tour_package_inclusion_item(package: GroupTourPackage) -> StructuredListItem:
    season = package.season if package.season in {"summer", "winter"} else ""
    details = [f"Guided {package.duration_days}-day Iceland programme — {season} group tour." if season else f"Guided {package.duration_days}-day Iceland group-tour programme."]
    pickup = display_time(package.pickup_time) or clean(package.pickup_time)
    if pickup and package.meeting_point: details.append(f"Pick-up: {pickup} from {package.meeting_point}.")
    elif pickup: details.append(f"Pick-up: {pickup}.")
    elif package.meeting_point: details.append(f"Meeting point: {package.meeting_point}.")
    accommodation = _accommodation_line(package.accommodation_policy)
    if accommodation: details.append(accommodation)
    if package.guide_policy: details.append("Guide: " + natural_join(unique(package.guide_policy)) + ".")
    if package.transport_policy: details.append("Transport: " + natural_join(unique(package.transport_policy)) + ".")
    programme = _programme_values(package)
    for index in range(0, len(programme), 8): details.append(("Programme highlights" if index == 0 else "Further programme highlights") + ": " + natural_join(programme[index:index+8]) + ".")
    details.append("The detailed daily programme is shown on the relevant itinerary days.")
    return StructuredListItem(label=package.title, detail_lines=tuple(details), source_row_ids=tuple(package.source_row_ids), category="group_tour")


def is_group_tour_commercial_day_visible(row: Mapping[str, Any]) -> bool:
    if row.get("group_tour_role") != "commercial_item": return True
    category, selected = str(row.get("group_tour_commercial_category") or ""), bool(row.get("group_tour_commercial_selected"))
    return category in ({"activity_upgrade", "transfer_package", "extra_hotel_night"} if selected else {"activity_upgrade"})
