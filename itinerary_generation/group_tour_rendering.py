"""Client-facing adapters for the canonical group-tour package contract.

The group-tour domain owns product and package-day facts.  This module converts
those facts into the shared render and structured-inclusion contracts without
re-parsing supplier prose in preview, editor, or PDF code.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

from itinerary_generation.group_tour_domain import (
    GroupTourAccommodationPolicy,
    GroupTourDay,
    GroupTourPackage,
    group_tour_day_from_row,
    group_tour_package_from_row,
)
from itinerary_generation.render_model import RenderBlock, RenderMetaLine, RenderSection
from itinerary_generation.structured_model import StructuredListItem
from itinerary_generation.time_display import display_time
from place_aliases import canonicalize_place_name
from shared.source_rows import source_row_id
from text_polish import polish_client_text, polish_title

_SPACE_RE = re.compile(r"\s+")
_REYKJAVIK_KEYS = {"reykjavik", "reykjavík"}
_TITLE_REPLACEMENTS = (
    (r"\bgolden circle\b", "Golden Circle"),
    (r"\bsouth coast\b", "South Coast"),
    (r"\bnorth iceland\b", "North Iceland"),
    (r"\bwest iceland\b", "West Iceland"),
    (r"\beast fjords?\b|\beastfjords\b", "East Fjords"),
    (r"\bglacier lagoon\b", "Glacier Lagoon"),
    (r"\bdiamond beach\b", "Diamond Beach"),
    (r"\bblack sand beach\b", "Black Sand Beach"),
    (r"\bice cave\b", "Ice Cave"),
)


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").replace("\xa0", " ")).strip(" \t\r\n-|:")


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _natural_join(values: Sequence[str]) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def group_tour_package_from_rows(rows: Iterable[Mapping[str, Any]]) -> GroupTourPackage | None:
    for row in rows or ():
        package = group_tour_package_from_row(row)
        if package is not None:
            return package
    return None


def group_tour_day_from_rows(rows: Iterable[Mapping[str, Any]]) -> GroupTourDay | None:
    for row in rows or ():
        segment = group_tour_day_from_row(row)
        if segment is not None:
            return segment
    return None


def group_tour_package_context_from_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    for row in rows or ():
        value = row.get("group_tour_package_context")
        if isinstance(value, Mapping):
            return dict(value)
    package = group_tour_package_from_rows(rows)
    if package is None:
        return {}
    return {
        "package_id": package.package_id,
        "title": package.title,
        "season": package.season,
        "duration_days": package.duration_days,
        "itinerary_start_day": package.itinerary_start_day,
        "itinerary_end_day": package.itinerary_end_day,
        "meeting_point": package.meeting_point,
        "pickup_time": package.pickup_time,
        "group_style": package.group_style,
        "commercial_status": package.commercial_status,
        "accommodation_policy": package.accommodation_policy.as_metadata,
        "warnings": list(package.warnings),
    }


def group_tour_day_title(rows: Iterable[Mapping[str, Any]]) -> str:
    segment = group_tour_day_from_rows(rows)
    if segment is None:
        return ""
    title = polish_title(segment.title)
    for pattern, replacement in _TITLE_REPLACEMENTS:
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    if title:
        title = title[:1].upper() + title[1:]
    return title or "Guided group tour"


def group_tour_day_city(rows: Iterable[Mapping[str, Any]]) -> str:
    """Return a stable display region for a package day without inventing a hotel."""

    row_list = list(rows or ())
    segment = group_tour_day_from_rows(row_list)
    if segment is not None:
        if segment.overnight_area:
            return polish_title(canonicalize_place_name(segment.overnight_area))
        route = [canonicalize_place_name(place) for place in segment.route if _clean(place)]
        non_capital = [place for place in route if place.casefold() not in _REYKJAVIK_KEYS]
        if non_capital:
            return polish_title(non_capital[-1])
        if route:
            return polish_title(route[-1])
    for row in row_list:
        city = canonicalize_place_name(row.get("city", ""))
        if city and not re.fullmatch(r"Day\s*\d+", city, flags=re.IGNORECASE):
            return polish_title(city)
    return "Iceland"


def group_tour_day_intro(rows: Iterable[Mapping[str, Any]]) -> str:
    row_list = list(rows or ())
    segment = group_tour_day_from_rows(row_list)
    if segment is None:
        return ""
    context = group_tour_package_context_from_rows(row_list)
    duration = int(context.get("duration_days") or 0)
    season = _clean(context.get("season"))
    title = group_tour_day_title(row_list)
    if segment.package_day_number == 1:
        lead = "Your guided group tour begins today"
        if duration:
            lead += f" on this {duration}-day programme"
        logistics: list[str] = []
        pickup = display_time(context.get("pickup_time", "")) or _clean(context.get("pickup_time"))
        meeting = _clean(context.get("meeting_point"))
        if pickup:
            if pickup.casefold().startswith("between "):
                logistics.append(f"pick-up {pickup[:1].lower() + pickup[1:]}")
            else:
                logistics.append(f"pick-up at {pickup}")
        if meeting:
            logistics.append(f"from {meeting}")
        logistics_text = " with " + " ".join(logistics) if logistics else ""
        season_text = f" {season}" if season in {"summer", "winter"} else ""
        return polish_client_text(f"{lead}{logistics_text}. The first{season_text} programme day focuses on {title}.")
    if duration and segment.package_day_number == duration:
        return polish_client_text(f"Complete your guided group tour with {title}, following the final planned route and conditions shown below.")
    return polish_client_text(f"Continue your guided group tour with {title}, following the day-by-day programme arranged for this stage of the journey.")


def _fact_description(segment: GroupTourDay) -> str:
    source = polish_client_text(segment.description)
    if source:
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", source) if item.strip()]
        useful: list[str] = []
        for sentence in sentences:
            lower = sentence.casefold()
            if any(marker in lower for marker in ("book this", "check availability", "what are you waiting", "price is per")):
                continue
            useful.append(sentence)
            if len(useful) >= 3:
                break
        # Preserve a later arrival/return/overnight fact when the opening prose
        # focuses only on sightseeing.  This keeps route continuity visible.
        for sentence in sentences[3:]:
            lower = sentence.casefold()
            if re.search(r"\b(return|head back|spend the night|overnight|accommodation)\b", lower):
                if sentence not in useful:
                    useful.append(sentence)
                break
        summary = " ".join(useful).strip()
        if summary:
            if len(summary) <= 720:
                return summary
            return summary[:717].rstrip(" ,;:") + "..."

    route = _unique(segment.route)
    highlights = _unique(segment.included_activities or segment.highlights)
    if route and highlights:
        return polish_client_text(
            f"Travel through {_natural_join(route)}, with planned visits including {_natural_join(highlights[:6])}."
        )
    if route:
        return polish_client_text(f"Travel through {_natural_join(route)}.")
    if highlights:
        return polish_client_text(f"Today’s guided programme includes {_natural_join(highlights[:6])}.")
    return ""


def _accommodation_display(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"\bw\s*/\s*breakfast\b", "breakfast included", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwith\s+breakfast\b", "breakfast included", text, flags=re.IGNORECASE)
    if text and not text.endswith((".", "!", "?")):
        text += "."
    return polish_client_text(text)


def build_group_tour_day_render_block(row: Mapping[str, Any]) -> RenderBlock | None:
    segment = group_tour_day_from_row(row)
    if segment is None:
        return None
    context = row.get("group_tour_package_context") if isinstance(row.get("group_tour_package_context"), Mapping) else {}
    duration = int(context.get("duration_days") or 0)
    section_title = f"Group Tour · Day {segment.package_day_number}"
    if duration:
        section_title += f" of {duration}"

    meta: list[RenderMetaLine] = []
    if segment.package_day_number == 1:
        pickup = display_time(context.get("pickup_time", "")) or _clean(context.get("pickup_time"))
        meeting = _clean(context.get("meeting_point"))
        if pickup:
            meta.append(RenderMetaLine("Pick-up", pickup))
        if meeting:
            meta.append(RenderMetaLine("Meeting point", meeting))
    if segment.route:
        meta.append(RenderMetaLine("Route", " → ".join(_unique(segment.route))))

    includes = _unique(segment.included_activities)[:8]
    extra_sections: list[RenderSection] = []
    if segment.meals:
        extra_sections.append(RenderSection("Meals", _unique(segment.meals)))
    if segment.accommodation_note:
        extra_sections.append(RenderSection("Included Overnight", [_accommodation_display(segment.accommodation_note)]))
    if segment.conditional_items:
        extra_sections.append(RenderSection("Important Conditions", [polish_client_text(item) for item in segment.conditional_items]))
    if segment.optional_items:
        extra_sections.append(RenderSection("Optional During This Tour Day", [polish_client_text(item) for item in segment.optional_items]))

    row_id = str(row.get("row_id") or "")
    return RenderBlock(
        kind="group_tour_day",
        row_id=row_id,
        section_title=section_title,
        title=group_tour_day_title([row]),
        meta=meta,
        includes=includes,
        description=_fact_description(segment),
        extra_sections=extra_sections,
        css_class="activity-block group-tour-day-block",
        source_row_ids=list(segment.source_row_ids) or ([row_id] if row_id else []),
        warnings=list(segment.warnings),
    )


def group_tour_package_route(package: GroupTourPackage | None) -> list[str]:
    if package is None:
        return []
    route: list[str] = []
    for segment in package.day_segments:
        for place in segment.route:
            canonical = canonicalize_place_name(place)
            if canonical and (not route or canonical != route[-1]):
                route.append(canonical)
    return route


def _package_accommodation_line(policy: GroupTourAccommodationPolicy) -> str:
    if not policy.included:
        return ""
    parts: list[str] = []
    if policy.nights:
        parts.append(f"{policy.nights} included night{'s' if policy.nights != 1 else ''}")
    else:
        parts.append("Included accommodation during the tour")
    if policy.room_basis:
        parts.append(policy.room_basis)
    if policy.bathroom:
        parts.append(policy.bathroom)
    if policy.meal_plan:
        parts.append(policy.meal_plan)
    wording = ", ".join(parts).rstrip(".") + "."
    if not policy.exact_properties_confirmed:
        wording += " Properties may vary according to availability."
    return polish_client_text(wording)


def group_tour_package_inclusion_item(package: GroupTourPackage) -> StructuredListItem:
    details: list[str] = []
    season = package.season if package.season in {"summer", "winter"} else ""
    if season:
        details.append(f"Guided {package.duration_days}-day Iceland programme — {season} group tour.")
    else:
        details.append(f"Guided {package.duration_days}-day Iceland group-tour programme.")
    pickup = display_time(package.pickup_time) or _clean(package.pickup_time)
    if pickup and package.meeting_point:
        details.append(f"Pick-up: {pickup} from {package.meeting_point}.")
    elif pickup:
        details.append(f"Pick-up: {pickup}.")
    elif package.meeting_point:
        details.append(f"Meeting point: {package.meeting_point}.")

    accommodation = _package_accommodation_line(package.accommodation_policy)
    if accommodation:
        details.append(accommodation)
    if package.guide_policy:
        details.append("Guide: " + _natural_join(_unique(package.guide_policy)) + ".")
    if package.transport_policy:
        details.append("Transport: " + _natural_join(_unique(package.transport_policy)) + ".")

    programme_values: list[str] = []
    # Explicit unnumbered package inclusions (for example an amphibian boat
    # ride confirmed in the supplier narrative) must not be pushed beyond the
    # visible highlight limit by generic Day N route bullets.
    for item in package.package_inclusions:
        is_numbered = bool(re.match(r"^Day\s*\d+", item, flags=re.IGNORECASE))
        clean = re.sub(r"^Day\s*\d+(?:\s*-\s*\d+)?\s*:\s*", "", item, flags=re.IGNORECASE)
        clean = re.sub(r"^and\s+", "", clean, flags=re.IGNORECASE)
        if re.search(r"\b(hotel|guesthouse|accommodation|private bathroom|breakfast|arrival|pick[-‑ ]?up|drop[- ]?off|minibus|vehicle|guide|wifi)\b", clean, re.IGNORECASE):
            continue
        if not is_numbered:
            programme_values.append(clean)
    programme_values.extend(
        item
        for segment in package.day_segments
        for item in segment.included_activities
    )
    for item in package.package_inclusions:
        if not re.match(r"^Day\s*\d+", item, flags=re.IGNORECASE):
            continue
        clean = re.sub(r"^Day\s*\d+(?:\s*-\s*\d+)?\s*:\s*", "", item, flags=re.IGNORECASE)
        if re.search(r"\b(hotel|guesthouse|accommodation|private bathroom|breakfast|arrival|pick[-‑ ]?up|drop[- ]?off|minibus|vehicle|guide|wifi)\b", clean, re.IGNORECASE):
            continue
        programme_values.append(clean)
    programme = _unique(programme_values)
    if programme:
        for index in range(0, len(programme), 8):
            label = "Programme highlights" if index == 0 else "Further programme highlights"
            details.append(f"{label}: " + _natural_join(programme[index:index + 8]) + ".")
    details.append("The detailed daily programme is shown on the relevant itinerary days.")
    return StructuredListItem(
        label=package.title,
        detail_lines=tuple(details),
        source_row_ids=tuple(package.source_row_ids),
        category="group_tour",
    )


def is_group_tour_commercial_day_visible(row: Mapping[str, Any]) -> bool:
    """Return whether a package-related commercial row belongs on a day page."""

    if row.get("group_tour_role") != "commercial_item":
        return True
    category = str(row.get("group_tour_commercial_category") or "")
    selected = bool(row.get("group_tour_commercial_selected"))
    if selected:
        return category in {"activity_upgrade", "transfer_package", "extra_hotel_night"}
    return category == "activity_upgrade"


__all__ = [
    "build_group_tour_day_render_block",
    "group_tour_day_city",
    "group_tour_day_from_rows",
    "group_tour_day_intro",
    "group_tour_day_title",
    "group_tour_package_context_from_rows",
    "group_tour_package_from_rows",
    "group_tour_package_inclusion_item",
    "group_tour_package_route",
    "is_group_tour_commercial_day_visible",
]
