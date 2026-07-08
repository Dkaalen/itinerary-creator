from __future__ import annotations

from pathlib import Path

from generator import group_rows_by_day
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_intro_writer import plan_day_intro_decision
from itinerary_generation.day_leisure_writer import plan_leisure_decision
from itinerary_generation.title_brain import plan_day_title_decision
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows

NORWAY_FIXTURE = Path(__file__).resolve().parent / "fixtures/real_inputs/norway_winter_output_quality_regression.txt"


def _norway_days():
    rows = normalize_itinerary_rows(parse_itinerary(NORWAY_FIXTURE.read_text(encoding="utf-8")))
    return group_rows_by_day(rows)


def test_title_decision_rejects_narrow_inclusions_when_broader_product_exists() -> None:
    grouped = _norway_days()

    day5 = plan_day_title_decision(grouped["Day 5"])
    assert day5.text == "Best of Bergen Private Walking Tour"
    assert day5.source == "activity_product_display_title"
    assert "narrow_inclusion_title" in {candidate.source for candidate in day5.rejected}
    assert any("cannot outrank" in candidate.rejected_reason for candidate in day5.rejected)

    day6 = plan_day_title_decision(grouped["Day 6"])
    assert day6.text == "Tromsø Private City Tour & Private Northern Lights Tour by Minibus"
    assert day6.source in {"schedule_composed_activity_title", "composed_activity_title"}
    assert "narrow_inclusion_title" in {candidate.source for candidate in day6.rejected}
    assert "Fjellheisen Cable Car" not in day6.text


def test_intro_and_leisure_decisions_have_non_fallback_sources() -> None:
    grouped = _norway_days()

    day1_facts = build_day_facts(grouped["Day 1"])
    day1_intent = classify_day_intent(day1_facts)
    day1_intro = plan_day_intro_decision(day1_facts, day1_intent)
    day1_leisure = plan_leisure_decision(day1_facts, day1_intent)

    assert day1_intro.source == "arrival_stay_intro"
    assert "fallback" not in day1_intro.source
    assert "transfer and stay details" not in day1_intro.text.lower()
    assert day1_leisure.source == "arrival_day_leisure"
    assert "remaining time is best kept simple" not in day1_leisure.text.lower()


def test_every_norway_day_title_has_traceable_non_last_resort_source() -> None:
    grouped = _norway_days()
    bad_sources = {"last_resort_title_fallback", "narrow_inclusion_title", "stay_title_fallback"}

    traces = {day: plan_day_title_decision(rows) for day, rows in grouped.items()}

    assert traces
    assert not {day: trace.source for day, trace in traces.items() if trace.source in bad_sources}
