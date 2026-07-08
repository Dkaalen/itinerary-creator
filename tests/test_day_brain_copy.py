from __future__ import annotations

from itinerary_generation.copy.visit_context import DayVisitContext
from itinerary_generation.day_copy_audit import audit_day_copy_cases
from itinerary_generation.day_copy_qa import FORBIDDEN_DAY_COPY_PHRASES, assert_day_copy_clean
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_leisure_writer import write_leisure_copy
from itinerary_generation.day_text import create_day_intro
from tests.fixtures.day_brain_cases import (
    ARRIVAL_ONWARD_ROWS,
    CRUISE_ONBOARD_ROWS,
    DAY_BRAIN_AUDIT_CASES,
    FULL_LEISURE_ROWS,
    RETURN_VISIT_ROWS,
    SAME_CITY_ACCOMMODATION_CHANGE_ROWS,
    TRAVEL_HEAVY_ROWS,
)


def _intro_and_leisure(rows, *, visit_context=None):
    facts = build_day_facts(rows, visit_context=visit_context)
    intent = classify_day_intent(facts)
    intro = create_day_intro(rows, visit_context=visit_context)
    leisure = write_leisure_copy(facts, intent)
    assert_day_copy_clean(facts=facts, intent=intent, intro=intro, leisure=leisure)
    return facts, intent, intro, leisure


def test_arrival_onward_travel_treats_arrival_city_as_transit():
    facts, intent, intro, leisure = _intro_and_leisure(ARRIVAL_ONWARD_ROWS)

    assert intent == "arrival_onward_travel"
    assert facts.arrival_city == "Helsinki"
    assert facts.end_city == "Rovaniemi"
    assert "Arrive in Helsinki" in intro
    assert "Rovaniemi" in intro
    assert "Welcome to Helsinki" not in intro
    assert "accommodation" not in intro.lower()
    assert leisure == "Keep any spare time practical today, with room for transfers, check-in and the arranged schedule."


def test_same_city_accommodation_change_is_not_rewelcomed():
    facts, intent, intro, _leisure = _intro_and_leisure(SAME_CITY_ACCOMMODATION_CHANGE_ROWS)

    assert intent == "same_city_accommodation_change"
    assert facts.same_city_accommodation_change is True
    assert "move to your next stay in Rovaniemi" in intro
    assert "Welcome to Rovaniemi" not in intro


def test_return_visit_copy_uses_return_context():
    visit_context = DayVisitContext(day="Day 7", city="Kiruna", canonical_city="Kiruna", visit_number=2, previous_days=("Day 2",))
    facts, intent, intro, _leisure = _intro_and_leisure(RETURN_VISIT_ROWS, visit_context=visit_context)

    assert facts.return_visit is True
    assert intent == "return_visit"
    assert intro.startswith("Return to Kiruna")
    assert "Welcome to" not in intro
    assert "first impressions" not in intro.lower()


def test_full_leisure_day_is_not_remaining_time():
    facts, intent, intro, leisure = _intro_and_leisure(FULL_LEISURE_ROWS)

    assert facts.full_leisure_day is True
    assert intent == "full_leisure_day"
    assert "Today is open for independent time in Rovaniemi" in intro
    assert "remaining time" not in intro.lower()
    assert "remaining time" not in leisure.lower()


def test_travel_heavy_day_does_not_overstate_free_time():
    facts, intent, intro, leisure = _intro_and_leisure(TRAVEL_HEAVY_ROWS)

    assert facts.travel_heavy is True
    assert intent == "overnight_transport_day"
    assert "overnight" in intro.lower()
    assert leisure == "Keep any spare time practical today, with room for transfers, check-in and the arranged schedule."


def test_cruise_onboard_leisure_is_context_aware():
    facts, intent, intro, leisure = _intro_and_leisure(CRUISE_ONBOARD_ROWS)

    assert intent == "cruise_day"
    assert "onboard" in intro.lower() or "sailing" in intro.lower()
    assert "ship facilities" in leisure


def test_day_brain_audit_cases_are_clean_and_reportable():
    report = audit_day_copy_cases(DAY_BRAIN_AUDIT_CASES)

    assert {item["case_id"] for item in report} == {case.case_id for case in DAY_BRAIN_AUDIT_CASES}
    assert all(not item["issue_codes"] for item in report)
    assert all(item["legacy_risk"] for item in report)


def test_forbidden_day_copy_phrases_do_not_appear_in_fixtures():
    for case in DAY_BRAIN_AUDIT_CASES:
        intro = create_day_intro(case.rows)
        facts = build_day_facts(case.rows)
        leisure = write_leisure_copy(facts, classify_day_intent(facts))
        combined = f"{intro} {leisure}".casefold()
        for phrase in FORBIDDEN_DAY_COPY_PHRASES:
            assert phrase.casefold() not in combined


def test_day_brain_refreshes_stale_generated_intro_but_preserves_manual_edit():
    from itinerary_generation.generated_ownership import resolve_intro

    refreshed = resolve_intro(
        day_edits={"intro": "Welcome to Helsinki. After check-in, enjoy your first impressions."},
        typed_day={},
        generated_intro="Arrive in Helsinki and continue to the central station for your onward train to Rovaniemi.",
        source_signature="sig",
    )
    manual = resolve_intro(
        day_edits={"intro": "Dennis custom intro", "intro_manual_override": True},
        typed_day={},
        generated_intro="Generated replacement",
        source_signature="sig",
    )

    assert refreshed.manual_override is False
    assert refreshed.intro.startswith("Arrive in Helsinki")
    assert manual.manual_override is True
    assert manual.intro == "Dennis custom intro"


def test_day_brain_refreshes_stale_generated_leisure_blocks_but_preserves_manual_blocks():
    from itinerary_generation.generated_ownership import resolve_blocks_html

    refreshed = resolve_blocks_html(
        day_edits={"blocks_html": "<p>Use the remaining time in Oslo unhurriedly.</p>"},
        typed_day={},
        generated_blocks_html="<p>Any open time in Oslo is left flexible for your own plans.</p>",
    )
    manual = resolve_blocks_html(
        day_edits={"blocks_html": "<p>My hand-written note.</p>", "blocks_manual_override": True},
        typed_day={},
        generated_blocks_html="<p>Generated replacement.</p>",
    )

    assert refreshed.manual_override is False
    assert "left flexible" in refreshed.html
    assert manual.manual_override is True
    assert "hand-written" in manual.html
