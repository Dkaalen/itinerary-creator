"""Travel-load scoring for day-brain copy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from itinerary_generation.day_timeline_events import TimelineEvent


@dataclass(frozen=True)
class TravelLoadProfile:
    """Deterministic travel intensity profile for a day."""

    level: str = "none"
    score: int = 0
    route_leg_count: int = 0
    local_transfer_count: int = 0
    has_overnight_transport: bool = False
    has_air_travel: bool = False
    has_port_or_station_transfer: bool = False
    is_travel_heavy: bool = False
    flags: frozenset[str] = field(default_factory=frozenset)


def classify_travel_load(events: Sequence[TimelineEvent]) -> TravelLoadProfile:
    """Score route and logistics intensity without writing prose."""

    route_events = tuple(event for event in events or () if event.is_route)
    local_transfers = tuple(event for event in events or () if event.is_local)
    route_leg_count = len(route_events)
    local_transfer_count = len(local_transfers)
    has_overnight = any(event.is_overnight and (event.is_route or event.mode in {"train", "cruise", "ferry"}) for event in events or ())
    has_air = any(event.mode == "flight" for event in events or ())
    has_port_or_station_transfer = any(event.target_kind in {"port", "station", "airport"} for event in local_transfers)

    score = 0
    score += route_leg_count * 2
    score += local_transfer_count
    if has_overnight:
        score += 3
    if has_air:
        score += 2
    if has_port_or_station_transfer:
        score += 1
    if route_leg_count >= 2:
        score += 1

    if has_overnight:
        level = "overnight"
    elif score >= 6:
        level = "full"
    elif score >= 4:
        level = "heavy"
    elif score >= 2:
        level = "moderate"
    elif score >= 1:
        level = "light"
    else:
        level = "none"

    flags: set[str] = set()
    if route_leg_count:
        flags.add(f"route_legs:{route_leg_count}")
    if local_transfer_count:
        flags.add(f"local_transfers:{local_transfer_count}")
    if has_overnight:
        flags.add("overnight_transport")
    if has_air:
        flags.add("air_travel")
    if has_port_or_station_transfer:
        flags.add("terminal_transfer")

    return TravelLoadProfile(
        level=level,
        score=score,
        route_leg_count=route_leg_count,
        local_transfer_count=local_transfer_count,
        has_overnight_transport=has_overnight,
        has_air_travel=has_air,
        has_port_or_station_transfer=has_port_or_station_transfer,
        is_travel_heavy=level in {"heavy", "full", "overnight"},
        flags=frozenset(flags),
    )


__all__ = ["TravelLoadProfile", "classify_travel_load"]
