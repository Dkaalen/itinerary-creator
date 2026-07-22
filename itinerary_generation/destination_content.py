"""Compose premium destination copy from explicit content owners."""
from __future__ import annotations

from dataclasses import dataclass

from itinerary_generation.destination_arc_content import arc_for_destination
from itinerary_generation.destination_arrival_content import arrival_focus_for_destination
from itinerary_generation.destination_content_lookup import resolve_destination
from itinerary_generation.destination_leisure_content import leisure_description, leisure_options_for
from itinerary_generation.destination_travel_day_content import travel_day_intro


@dataclass(frozen=True)
class DestinationCopy:
    arc: str
    leisure_options: tuple[tuple[str, tuple[str, ...]], ...]
    arrival_focus: str


def destination_copy(value: object) -> DestinationCopy:
    resolved = resolve_destination(value)
    if not resolved.name:
        return DestinationCopy(
            arc="Time to explore at your own pace",
            leisure_options=leisure_options_for("", None),
            arrival_focus="local scenery and destination character",
        )
    return DestinationCopy(
        arc=arc_for_destination(resolved.name, resolved.record),
        leisure_options=leisure_options_for(resolved.name, resolved.record),
        arrival_focus=arrival_focus_for_destination(resolved.record),
    )


def destination_arc_fallback(value: object) -> str:
    return destination_copy(value).arc


__all__ = [
    "DestinationCopy", "destination_arc_fallback", "destination_copy",
    "leisure_description", "travel_day_intro",
]
