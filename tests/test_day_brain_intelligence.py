from __future__ import annotations

from itinerary_generation.copy.visit_context import build_day_visit_contexts
from itinerary_generation.day_accommodation_state import build_accommodation_state
from itinerary_generation.day_copy_variation import choose_copy_variant
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_timeline_events import normalize_day_events, summarize_timeline_events
from itinerary_generation.day_travel_load import classify_travel_load
from tests.fixtures.day_brain_cases import (
    ARRIVAL_ONWARD_ROWS,
    RETURN_VISIT_ROWS,
    SAME_CITY_ACCOMMODATION_CHANGE_ROWS,
    TRAVEL_HEAVY_ROWS,
)


def test_timeline_event_normalizer_identifies_transit_and_route_events():
    events = normalize_day_events(ARRIVAL_ONWARD_ROWS)
    summary = summarize_timeline_events(events)

    assert [event.kind for event in events] == ["arrival", "local_transfer", "route_transport"]
    assert events[1].target_kind == "station"
    assert events[2].origin == "Helsinki"
    assert events[2].destination == "Rovaniemi"
    assert events[2].is_overnight is True
    assert summary.route_leg_count == 1
    assert summary.local_transfer_count == 1


def test_accommodation_state_machine_detects_same_city_move():
    events = normalize_day_events(SAME_CITY_ACCOMMODATION_CHANGE_ROWS)
    state = build_accommodation_state(events)

    assert state.has_accommodation is True
    assert state.accommodation_change is True
    assert state.same_city_change is True
    assert state.new_city_change is False
    assert state.tonight_city == "Rovaniemi"


def test_travel_load_scores_overnight_multileg_days_as_heavy():
    events = normalize_day_events(TRAVEL_HEAVY_ROWS)
    profile = classify_travel_load(events)
    facts = build_day_facts(TRAVEL_HEAVY_ROWS)

    assert profile.level == "overnight"
    assert profile.route_leg_count >= 2
    assert profile.local_transfer_count >= 2
    assert profile.is_travel_heavy is True
    assert facts.travel_load.level == "overnight"
    assert facts.travel_heavy is True


def test_destination_memory_marks_return_visits_not_transit_cities():
    grouped = {
        "Day 1": [dict(RETURN_VISIT_ROWS[0], day="Day 1"), dict(RETURN_VISIT_ROWS[1], day="Day 1")],
        "Day 2": [dict(RETURN_VISIT_ROWS[0], day="Day 2"), dict(RETURN_VISIT_ROWS[1], day="Day 2")],
    }

    contexts = build_day_visit_contexts(grouped)

    assert contexts["Day 1"].is_return_visit is False
    assert contexts["Day 2"].is_return_visit is True
    assert contexts["Day 2"].previous_days == ("Day 1",)


def test_copy_variation_is_deterministic_and_approved_only():
    facts = build_day_facts(ARRIVAL_ONWARD_ROWS)
    options = ("Approved one.", "Approved two.", "Approved three.")

    first = choose_copy_variant(options, facts, "arrival_onward_travel")
    second = choose_copy_variant(options, facts, "arrival_onward_travel")

    assert first == second
    assert first in options
