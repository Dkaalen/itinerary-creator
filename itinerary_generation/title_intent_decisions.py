"""Day-title policy for arrival, departure and accommodation-change intents."""

from __future__ import annotations

from typing import Mapping, Sequence

from itinerary_generation.common import get_row_type
from itinerary_generation.copy_decision_contract import (
    CopyDecisionCandidate,
    CopyDecisionTrace,
    finalize_decision,
)
from itinerary_generation.day_facts import DayFacts
from itinerary_generation.day_intent import DayIntent
from itinerary_generation.title_decision_helpers import clean_title_value, title_trace
from place_aliases import country_for_place
from text_polish import polish_title


def departure_or_stay_change_title(
    *,
    row_list: Sequence[Mapping[str, object]],
    facts: DayFacts,
    intent: DayIntent,
    city: str,
    raw_day_text: str,
    primary_transport_candidate: CopyDecisionCandidate | None,
    context: Mapping[str, str],
) -> CopyDecisionTrace | None:
    if intent == DayIntent.DEPARTURE_DAY:
        if not facts.has_departure and primary_transport_candidate:
            return finalize_decision(
                kind="day_title",
                selected=primary_transport_candidate,
                candidates=(primary_transport_candidate,),
                context=dict(context) | {"departure_transfer_only": True},
            )
        return title_trace(
            f"Departure from {city}" if city else "Departure",
            source="departure_intent_title",
            priority=78,
            reason="Departure-day intent owns the day title.",
            context=context,
        )

    if intent != DayIntent.SAME_CITY_ACCOMMODATION_CHANGE:
        return None

    hotel_rows = [row for row in row_list if get_row_type(dict(row)) == "Hotel"]
    hotel_titles = [
        clean_title_value(row.get("title") or row.get("hotel_name") or row.get("original_title"))
        for row in hotel_rows
    ]
    hotel_text = " ".join(
        clean_title_value(row.get(key))
        for row in hotel_rows
        for key in ("title", "hotel_name", "original_title", "room_category", "details")
    ).lower()
    for hotel_title in hotel_titles:
        if "snow hotel" in hotel_title.lower() or "snowhotel" in hotel_title.lower():
            title = (
                "Arctic Snow Hotel Stay"
                if "arctic" in hotel_title.lower()
                else f"{polish_title(hotel_title)} Stay"
            )
            return title_trace(
                title,
                source="distinctive_accommodation_title",
                priority=90,
                reason="Distinctive accommodation owns this same-city move title.",
                context=context,
            )
    if "glass igloo" in hotel_text or "igloo" in hotel_text:
        return title_trace(
            f"Glass Igloo Stay in {city}" if city else "Glass Igloo Stay",
            source="distinctive_accommodation_title",
            priority=90,
            reason="Distinctive glass-igloo stay owns this day title.",
            context=context,
        )
    if facts.return_visit and "next accommodation" not in raw_day_text:
        return title_trace(
            f"Return to {city}" if city else "Return Visit",
            source="return_visit_title",
            priority=80,
            reason="Visit context marks this as a return stay.",
            context=context,
        )
    return title_trace(
        f"Next Stay in {city}" if city else "Next Stay",
        source="accommodation_change_title",
        priority=76,
        reason="Same-city accommodation change owns this day title.",
        context=context,
    )


def arrival_or_return_title(
    *,
    facts: DayFacts,
    intent: DayIntent,
    city: str,
    activities: Sequence[Mapping[str, object]],
    primary_transport_candidate: CopyDecisionCandidate | None,
    context: Mapping[str, str],
) -> CopyDecisionTrace | None:
    if intent == DayIntent.ARRIVAL_ONWARD_TRAVEL:
        destination = polish_title(facts.onward_destination or facts.end_city or "")
        return title_trace(
            f"Arrival and travel to {destination}" if destination else "Arrival and travel day",
            source="arrival_onward_title",
            priority=82,
            reason="Arrival plus onward-travel intent owns this day title.",
            candidates=(primary_transport_candidate,),
            context=context,
        )

    if intent == DayIntent.OVERNIGHT_TRANSPORT_DAY and facts.has_cruise and facts.has_leisure_row:
        origin = polish_title(facts.start_city or city)
        destination = polish_title(facts.end_city or facts.route_destination)
        if origin and destination and origin.casefold() != destination.casefold():
            return title_trace(
                f"{origin} at Leisure and Overnight Cruise to {destination}",
                source="leisure_overnight_cruise_title",
                priority=94,
                reason="The day combines genuine leisure at the departure city with an overnight cruise to the next destination.",
                candidates=(primary_transport_candidate,),
                context=context,
            )

    if intent == DayIntent.ARRIVAL_STAY and city and not activities:
        return _arrival_stay_title(
            facts=facts,
            city=city,
            primary_transport_candidate=primary_transport_candidate,
            context=context,
        )

    if intent == DayIntent.RETURN_VISIT:
        return title_trace(
            f"Return to {city}" if city else "Return Visit",
            source="return_visit_title",
            priority=80,
            reason="Itinerary day state marks this as a genuine return chapter.",
            context=context,
        )

    if (
        facts.has_route_transport
        and not activities
        and primary_transport_candidate
        and (facts.has_train or facts.has_flight or facts.has_ferry or facts.has_cruise)
    ):
        return finalize_decision(
            kind="day_title",
            selected=primary_transport_candidate,
            candidates=(primary_transport_candidate,),
            context=context,
        )
    return None


def _arrival_stay_title(
    *,
    facts: DayFacts,
    city: str,
    primary_transport_candidate: CopyDecisionCandidate | None,
    context: Mapping[str, str],
) -> CopyDecisionTrace:
    if facts.return_visit:
        return title_trace(
            f"Return to {city}",
            source="return_visit_title",
            priority=80,
            reason="Visit context marks this as a return stay.",
            context=context,
        )
    if country_for_place(city) == "Iceland":
        return title_trace(
            "Welcome to Iceland",
            source="arrival_country_title",
            priority=78,
            reason="Iceland arrival title uses country-level welcome wording.",
            context=context,
        )
    if facts.has_flight or "arrival_airport_transfer" in facts.source_flags:
        return title_trace(
            f"Welcome to {city}",
            source="arrival_intent_title",
            priority=88,
            reason="Arrival and destination accommodation own the day title; inbound flight wording is supporting logistics.",
            candidates=(primary_transport_candidate,),
            context=context,
        )
    if facts.has_route_transport and primary_transport_candidate:
        return finalize_decision(
            kind="day_title",
            selected=primary_transport_candidate,
            candidates=(primary_transport_candidate,),
            context=dict(context) | {"arrival_stay": True, "overnight_destination": city},
        )
    if facts.has_route_transport:
        return title_trace(
            f"Arrival in {city}",
            source="arrival_intent_title",
            priority=86,
            reason="Arrival at the overnight destination owns the title while the route remains visible in the day intro and travel block.",
            candidates=(primary_transport_candidate,),
            context=context,
        )
    return title_trace(
        f"Welcome to {city}",
        source="arrival_intent_title",
        priority=78,
        reason="Arrival-stay intent owns this day title.",
        context=context,
    )


__all__ = ["arrival_or_return_title", "departure_or_stay_change_title"]
