"""Normalize raw day rows into factual timeline events."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from itinerary_generation.airport_transfer_contract import airport_transfer_facts
from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_optional_row
from itinerary_generation.destination_validation import is_valid_destination_city
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_domain.route_summary import transport_endpoints_from_row
from itinerary_generation.transport_safety import base_destination_from_terminal
from place_aliases import canonicalize_place_name
from shared.source_rows import source_row_id
from text_polish import polish_title

_STATION_WORDS = ("station", "airport", "harbour", "harbor", "port", "terminal", "pier", "dock")
_ACCOMMODATION_WORDS = ("hotel", "accommodation", "resort", "cabin", "igloo", "lodge", "apartment")
_LEISURE_MARKERS = ("leisure", "free time", "free day", "at your own pace", "open day", "own arrangements")
_OVERNIGHT_MARKERS = ("overnight", "night train", "sleeper", "sleeping compartment", "night ferry", "night cruise")
_TRANSPORT_TYPES = set(TRANSPORT_TYPES) | {"Transfer", "Transport", "Coach", "Bus"}


def clean_event_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def source_text_for_event(row: Mapping[str, Any]) -> str:
    return clean_event_text(
        " ".join(
            str(row.get(key, "") or "")
            for key in (
                "type",
                "effective_type",
                "city",
                "title",
                "original_title",
                "details",
                "description",
                "meeting_point",
                "end_point",
                "hotel_name",
                "room_category",
            )
        )
    )


def canonical_event_city(value: object) -> str:
    raw = clean_event_text(value)
    if not raw:
        return ""
    raw = base_destination_from_terminal(raw) or raw
    raw = re.sub(
        r"\s+(?:central\s+station|railway\s+station|train\s+station|bus\s+station|airport|ferry\s+terminal|cruise\s+terminal|terminal|harbou?r|port)$",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip(" -:|.,")
    city = polish_title(canonicalize_place_name(raw) or raw)
    if not city or not is_valid_destination_city(city):
        return ""
    return city


def _best_city_from_phrase(value: str, *, prefer_suffix: bool = False) -> str:
    words = [word for word in re.split(r"\s+", clean_event_text(value)) if word]
    if prefer_suffix:
        for size in range(1, min(3, len(words)) + 1):
            city = canonical_event_city(" ".join(words[-size:]))
            if city:
                return city
    city = canonical_event_city(value)
    if city:
        return city
    for size in range(min(3, len(words)), 0, -1):
        city = canonical_event_city(" ".join(words[:size]))
        if city:
            return city
    return ""


def _fallback_transport_endpoints(text: str) -> tuple[str, str]:
    place = r"[A-ZÀ-Ý][A-Za-zÀ-ÿøØåÅäÄöÖ .\'-]+?"
    matches = list(re.finditer(rf"\b(?P<origin>{place})\s+to\s+(?P<destination>{place})(?:\s+-|\s+\||,|$)", text))
    if not matches:
        return "", ""
    match = matches[-1]
    return _best_city_from_phrase(match.group("origin"), prefer_suffix=True), _best_city_from_phrase(match.group("destination"))


def _transport_endpoints(row: Mapping[str, Any], row_type: str) -> tuple[str, str]:
    if row_type not in _TRANSPORT_TYPES:
        return "", ""
    if row_type == "Transfer" and not is_route_transfer(dict(row)):
        return "", ""
    origin, destination = transport_endpoints_from_row(dict(row))
    origin_city, destination_city = canonical_event_city(origin), canonical_event_city(destination)
    if (not origin_city or not destination_city) and row_type != "Transfer":
        fallback_origin, fallback_destination = _fallback_transport_endpoints(source_text_for_event(row))
        origin_city = origin_city or fallback_origin
        destination_city = destination_city or fallback_destination
    return origin_city, destination_city


def _event_kind(row_type: str, text: str, *, is_route: bool) -> str:
    lower = text.lower()
    if row_type == "Arrival":
        return "arrival"
    if row_type == "Departure":
        return "departure"
    if row_type == "Hotel":
        return "accommodation"
    if row_type == "Cruise" and any(marker in lower for marker in _LEISURE_MARKERS):
        return "onboard_leisure"
    if row_type == "Leisure" or any(marker in lower for marker in _LEISURE_MARKERS):
        return "leisure"
    if row_type in _TRANSPORT_TYPES:
        return "route_transport" if is_route else "local_transfer"
    if row_type == "Activity":
        return "activity"
    return "other"


def _mode(row_type: str, text: str) -> str:
    lower = text.lower()
    if row_type in {"Coach", "Bus"} or "coach" in lower or " bus" in f" {lower}":
        return "coach"
    if row_type == "Flight" or "flight" in lower:
        return "flight"
    if row_type == "Train" or "train" in lower or "rail" in lower:
        return "train"
    if row_type == "Ferry" or "ferry" in lower:
        return "ferry"
    if row_type == "Cruise" or "cruise" in lower or "sailing" in lower:
        return "cruise"
    if row_type == "Transfer":
        return "transfer"
    if row_type in {"Transport", "Coach", "Bus"}:
        return row_type.lower()
    return ""


def _target_kind(text: str, row_type: str) -> str:
    lower = text.lower()
    target_text = lower
    to_match = re.search(r"\bto\s+(.+)$", lower)
    if to_match:
        target_text = to_match.group(1)
    if any(word in target_text for word in ("central station", "railway station", "train station", "station")):
        return "station"
    # Airport must be checked before port: the substring "port" occurs in
    # "airport" and previously turned airport transfers into port transfers.
    if any(word in target_text for word in ("airport", "flight terminal")):
        return "airport"
    if any(word in target_text for word in ("ferry terminal", "cruise terminal", "harbour", "harbor", "port", "pier", "dock")):
        return "port"
    if row_type == "Hotel" or any(word in target_text for word in _ACCOMMODATION_WORDS):
        return "accommodation"
    return ""


@dataclass(frozen=True)
class TimelineEvent:
    """One normalized row-level event used by day facts and QA."""

    source_row_id: str
    order: int
    row_type: str
    kind: str
    city: str = ""
    origin: str = ""
    destination: str = ""
    mode: str = ""
    target_kind: str = ""
    text: str = ""
    is_route: bool = False
    is_local: bool = False
    is_overnight: bool = False
    is_leisure: bool = False
    flags: frozenset[str] = field(default_factory=frozenset)

    @property
    def route_endpoint(self) -> str:
        return self.destination or self.origin


@dataclass(frozen=True)
class TimelineEventSummary:
    """Compact event summary for audit scripts and tests."""

    event_count: int = 0
    route_leg_count: int = 0
    local_transfer_count: int = 0
    accommodation_count: int = 0
    activity_count: int = 0
    leisure_count: int = 0
    overnight_transport_count: int = 0
    cities: tuple[str, ...] = ()


def normalize_day_events(rows: Sequence[Mapping[str, Any]] | None) -> tuple[TimelineEvent, ...]:
    """Return factual timeline events from day rows without copy decisions."""

    events: list[TimelineEvent] = []
    for index, raw_row in enumerate(rows or []):
        if not isinstance(raw_row, Mapping) or is_optional_row(dict(raw_row)):
            continue
        row = dict(raw_row)
        row_type = get_row_type(row)
        text = source_text_for_event(row)
        lower = text.lower()
        origin, destination = _transport_endpoints(row, row_type)
        is_route = bool(destination or origin) and row_type in _TRANSPORT_TYPES and not (row_type == "Transfer" and not is_route_transfer(row))
        kind = _event_kind(row_type, text, is_route=is_route)
        is_local = kind == "local_transfer"
        city = canonical_event_city(row.get("city", "")) or destination or origin
        flags: set[str] = set()
        target_kind = _target_kind(text, row_type)
        if target_kind:
            flags.add(f"target:{target_kind}")
        if is_route:
            flags.add("route")
        if is_local:
            flags.add("local")
        if any(marker in lower for marker in _OVERNIGHT_MARKERS):
            flags.add("overnight")
        if "check-in" in lower or "check in" in lower:
            flags.add("check_in")
        if "check-out" in lower or "check out" in lower:
            flags.add("check_out")
        if row_type == "Transfer":
            airport_facts = airport_transfer_facts(row)
            if airport_facts.direction == "departure":
                flags.add("departure_airport_transfer")
            elif airport_facts.direction == "arrival":
                flags.add("arrival_airport_transfer")
            elif airport_facts.is_airport_transfer:
                flags.add("airport_transfer_direction_unknown")
        events.append(
            TimelineEvent(
                source_row_id=source_row_id(row, index),
                order=index,
                row_type=row_type,
                kind=kind,
                city=city,
                origin=origin,
                destination=destination,
                mode=_mode(row_type, text),
                target_kind=target_kind,
                text=text,
                is_route=is_route,
                is_local=is_local,
                is_overnight="overnight" in flags,
                is_leisure=kind in {"leisure", "onboard_leisure"},
                flags=frozenset(flags),
            )
        )
    return tuple(events)


def summarize_timeline_events(events: Sequence[TimelineEvent]) -> TimelineEventSummary:
    cities: list[str] = []
    for event in events or []:
        for city in (event.origin, event.destination, event.city):
            if city and city not in cities:
                cities.append(city)
    return TimelineEventSummary(
        event_count=len(tuple(events or ())),
        route_leg_count=sum(1 for event in events if event.is_route),
        local_transfer_count=sum(1 for event in events if event.is_local),
        accommodation_count=sum(1 for event in events if event.kind == "accommodation"),
        activity_count=sum(1 for event in events if event.kind == "activity"),
        leisure_count=sum(1 for event in events if event.is_leisure),
        overnight_transport_count=sum(1 for event in events if event.is_overnight and event.is_route),
        cities=tuple(cities),
    )


__all__ = [
    "TimelineEvent",
    "TimelineEventSummary",
    "canonical_event_city",
    "clean_event_text",
    "normalize_day_events",
    "source_text_for_event",
    "summarize_timeline_events",
]
