"""Destination identity and arrival wording inputs for day intros."""
from __future__ import annotations

from itinerary_generation.day_facts import DayFacts, row_text
from itinerary_generation.day_intro_context import _clean
from itinerary_generation.destination_profile_builder import destination_profile_for
from place_aliases import country_for_place


def _destination_identity(city: str) -> str:
    profile = destination_profile_for(city)
    return profile.arrival_identity or profile.identity or city


def _arrival_display_place(facts: DayFacts, city: str) -> str:
    if "arrival_airport_transfer" in facts.source_flags and country_for_place(city) == "Iceland":
        return "Iceland"
    return city


def _arrival_transfer_clause(facts: DayFacts) -> str:
    """Return a client-facing arrival logistics clause, not admin/report copy."""

    text = " ".join(row_text(row) for row in facts.rows).lower()
    if "flybus" in text:
        return "the arranged Flybus transfer brings you towards your accommodation area"
    if "self transfer" in text or "self-transfer" in text or "self arranged" in text or "self-arranged" in text:
        return "follow the self-arranged transfer details to reach your accommodation"
    if facts.has_transfer:
        return "your arranged transfer brings you to your accommodation"
    return "the schedule is kept simple around your arrival"


def _arrival_stay_intro(facts: DayFacts, city: str) -> str:
    place = _arrival_display_place(facts, city or "the destination") if city else "the destination"
    identity = _destination_identity(city or place)
    if facts.return_visit:
        return f"Return to {place}. After arrival, the day stays light so you can settle back in around the listed arrangements."
    transfer_clause = _arrival_transfer_clause(facts)
    if facts.has_transfer or facts.has_flight:
        return f"Welcome to {place}. After arrival, {transfer_clause}, then the rest of the day stays light so you can settle in and get a feel for {identity}."
    return f"Welcome to {place}. The day stays light, with time to settle in and get a feel for {identity}."
