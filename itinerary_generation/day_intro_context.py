"""Immutable fact/intent context and shared day-intro primitives."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from itinerary_generation.common import get_row_type
from itinerary_generation.day_facts import DayFacts, row_text
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from shared.text import clean_space
from text_polish import polish_title

@dataclass(frozen=True)
class DayIntroContext:
    facts: DayFacts
    intent: DayIntent
    city: str
    mode: str


def build_day_intro_context(facts: DayFacts, intent: DayIntent | None = None) -> DayIntroContext:
    resolved_intent = intent or classify_day_intent(facts)
    return DayIntroContext(facts=facts, intent=resolved_intent, city=_main_city(facts), mode=_mode(facts))


def _clean(value: object) -> str:
    return clean_space(value)


def _city(value: object) -> str:
    return polish_title(_clean(value))


def _main_city(facts: DayFacts) -> str:
    return _city(facts.main_city or facts.end_city or facts.overnight_city or facts.arrival_city or facts.start_city)


def _mode(facts: DayFacts) -> str:
    if facts.has_self_drive:
        return "self-drive route"
    if facts.has_overnight_transport and facts.has_cruise:
        return "cruise"
    if facts.has_overnight_transport and facts.has_train:
        return "train"
    if facts.has_flight:
        return "flight"
    if facts.has_train:
        return "train"
    if facts.has_ferry:
        return "ferry"
    if facts.has_cruise:
        return "cruise"
    return "transfer" if facts.has_transfer else "travel"


def _travel_phrase(facts: DayFacts, *, imperative: bool = False) -> str:
    origin = _city(facts.route_origin or facts.start_city)
    destination = _city(facts.route_destination or facts.end_city or facts.onward_destination)
    if facts.has_self_drive:
        verb = "Continue driving" if imperative else "Drive"
        if origin and destination and origin.casefold() != destination.casefold():
            return f"{verb} from {origin} to {destination}"
        if destination:
            return f"{verb} to {destination}"
        return f"{verb} along the listed route"
    mode = _mode(facts)
    verb = "Continue" if imperative else "Travel"
    if origin and destination and origin.casefold() != destination.casefold():
        return f"{verb} from {origin} to {destination} by {mode}"
    if destination:
        return f"{verb} to {destination} by {mode}"
    return f"{verb} with the listed travel arrangements"


def _has_station_transfer(facts: DayFacts) -> bool:
    text = " ".join(row_text(row) for row in facts.rows).lower()
    return any(marker in text for marker in ("central station", "railway station", "train station", "station"))


def _has_port_transfer(facts: DayFacts) -> bool:
    text = " ".join(row_text(row) for row in facts.rows).lower()
    return any(marker in text for marker in ("cruise terminal", "ferry terminal", "harbour", "harbor", "port"))


def _activity_rows(facts: DayFacts) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for row in facts.rows:
        if get_row_type(dict(row)) != "Activity":
            continue
        text = row_text(row).lower()
        if "leisure" in text or "free time" in text:
            continue
        rows.append(row)
    return rows
