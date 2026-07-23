from __future__ import annotations

from collections import OrderedDict

from itinerary_generation.copy.visit_context import build_day_visit_contexts
from itinerary_generation.day_copy_qa import find_day_copy_issues
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import DayIntent, classify_day_intent
from itinerary_generation.render_document_builder import build_render_document
from itinerary_generation.title_brain import plan_day_title_decision


def _row(day: str, row_type: str, city: str, title: str, details: str = "") -> dict:
    return {
        "day": day,
        "type": row_type,
        "source_type": row_type,
        "effective_type": row_type,
        "city": city,
        "title": title,
        "original_title": title,
        "details": details,
    }


def _group(rows: list[dict]) -> OrderedDict[str, list[dict]]:
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for row in rows:
        grouped.setdefault(row["day"], []).append(row)
    return grouped


def _oslo_split_stay() -> tuple[list[dict], OrderedDict[str, list[dict]]]:
    rows = [
        _row("Day 1", "Arrival", "Oslo", "Welcome to Norway", "Arrival in Oslo"),
        _row("Day 1", "Transfer", "Oslo", "Private transfer to your accommodation", "Oslo Airport to Oslo hotel"),
        _row("Day 1", "Hotel", "Oslo", "Thon Hotel Opera", "2 nights"),
        _row("Day 2", "Activity", "Oslo", "Oslo Walking Tour", "10:00 AM - 12:00 PM"),
        _row("Day 3", "Hotel", "Oslo", "Radisson Blu Plaza", "2 nights"),
        _row("Day 4", "Activity", "Oslo", "Electric Oslofjord Sightseeing Cruise", "11:00 AM - 1:00 PM"),
    ]
    return rows, _group(rows)


def test_itinerary_state_turns_hotel_only_same_city_day_into_accommodation_change():
    rows, grouped = _oslo_split_stay()
    contexts = build_day_visit_contexts(grouped)
    facts = build_day_facts(grouped["Day 3"], visit_context=contexts["Day 3"])

    assert contexts["Day 3"].chapter_start is False
    assert contexts["Day 3"].previous_overnight_city == "Oslo"
    assert facts.day_state.chapter_continuation is True
    assert facts.day_state.same_city_accommodation_change is True
    assert facts.day_state.welcome_allowed is False
    assert classify_day_intent(facts) == DayIntent.SAME_CITY_ACCOMMODATION_CHANGE

    rendered = build_render_document(rows, grouped)
    day3 = next(day for day in rendered.days if day.day == "Day 3")
    assert day3.title == "Next Stay in Oslo"
    assert day3.intro.startswith("Today you move to your next stay in Oslo")
    assert "Welcome to Oslo" not in f"{day3.title} {day3.intro}"


def test_first_hotel_only_destination_day_can_still_use_welcome_copy():
    rows = [_row("Day 1", "Hotel", "Rovaniemi", "Original Sokos Hotel Vaakuna", "2 nights")]
    grouped = _group(rows)
    context = build_day_visit_contexts(grouped)["Day 1"]
    facts = build_day_facts(rows, visit_context=context)

    assert context.chapter_start is True
    assert facts.day_state.arrival_stay is True
    assert facts.day_state.welcome_allowed is True
    assert classify_day_intent(facts) == DayIntent.ARRIVAL_STAY
    assert plan_day_title_decision(rows, visit_context=context).text == "Welcome to Rovaniemi"


def test_repeated_same_city_arrival_row_does_not_create_a_new_visit_or_welcome():
    rows = [
        _row("Day 1", "Arrival", "Oslo", "Arrival in Oslo"),
        _row("Day 1", "Hotel", "Oslo", "Thon Hotel Opera", "1 night"),
        _row("Day 2", "Arrival", "Oslo", "Arrival in Oslo", "Local arrival logistics"),
        _row("Day 2", "Hotel", "Oslo", "Radisson Blu Plaza", "1 night"),
    ]
    grouped = _group(rows)
    contexts = build_day_visit_contexts(grouped)
    facts = build_day_facts(grouped["Day 2"], visit_context=contexts["Day 2"])

    assert contexts["Day 2"].chapter_start is False
    assert contexts["Day 2"].is_return_visit is False
    assert facts.day_state.welcome_allowed is False
    assert classify_day_intent(facts) == DayIntent.SAME_CITY_ACCOMMODATION_CHANGE

    rendered = build_render_document(rows, grouped)
    day2 = next(day for day in rendered.days if day.day == "Day 2")
    assert day2.title == "Next Stay in Oslo"
    assert "Welcome to Oslo" not in f"{day2.title} {day2.intro}"


def test_real_return_after_leaving_city_keeps_return_visit_language():
    rows = [
        _row("Day 1", "Arrival", "Oslo", "Arrival in Oslo"),
        _row("Day 1", "Hotel", "Oslo", "Oslo Hotel", "1 night"),
        _row("Day 2", "Train", "Bergen", "Train Oslo to Bergen"),
        _row("Day 2", "Hotel", "Bergen", "Bergen Hotel", "1 night"),
        _row("Day 3", "Train", "Oslo", "Train Bergen to Oslo"),
        _row("Day 3", "Hotel", "Oslo", "Oslo Airport Hotel", "1 night"),
    ]
    grouped = _group(rows)
    contexts = build_day_visit_contexts(grouped)
    facts = build_day_facts(grouped["Day 3"], visit_context=contexts["Day 3"])

    assert contexts["Day 3"].chapter_start is True
    assert contexts["Day 3"].is_return_visit is True
    assert facts.day_state.return_visit is True
    assert facts.day_state.welcome_allowed is False
    assert classify_day_intent(facts) == DayIntent.RETURN_VISIT

    rendered = build_render_document(rows, grouped)
    day3 = next(day for day in rendered.days if day.day == "Day 3")
    assert day3.title == "Return to Oslo"
    assert "Welcome to Oslo" not in f"{day3.title} {day3.intro}"


def test_intercity_route_and_hotel_remains_travel_owned_not_generic_welcome():
    rows = [
        _row("Day 1", "Hotel", "Oslo", "Oslo Hotel", "1 night"),
        _row("Day 2", "Train", "Bergen", "Train Oslo to Bergen"),
        _row("Day 2", "Hotel", "Bergen", "Bergen Hotel", "2 nights"),
    ]
    grouped = _group(rows)
    context = build_day_visit_contexts(grouped)["Day 2"]
    facts = build_day_facts(grouped["Day 2"], visit_context=context)

    assert context.chapter_start is True
    assert facts.day_state.arrival_stay is False
    assert classify_day_intent(facts) == DayIntent.TRAVEL_DAY
    title = plan_day_title_decision(grouped["Day 2"], visit_context=context).text
    assert title != "Welcome to Bergen"


def test_day_copy_qa_uses_day_state_to_reject_non_arrival_welcome_copy():
    _rows, grouped = _oslo_split_stay()
    context = build_day_visit_contexts(grouped)["Day 3"]
    facts = build_day_facts(grouped["Day 3"], visit_context=context)
    issues = find_day_copy_issues(
        facts=facts,
        intent=classify_day_intent(facts),
        intro="Welcome to Oslo. Settle into your hotel.",
    )

    assert [issue.code for issue in issues] == ["non_arrival_welcome"]


def test_day_state_is_the_single_itinerary_arrival_authority():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    production = root / "itinerary_generation"
    callers = []
    for path in production.rglob("*.py"):
        if path.name == "day_state.py":
            continue
        source = path.read_text(encoding="utf-8")
        if "build_day_state(" in source:
            callers.append(path.relative_to(root).as_posix())

    assert callers == ["itinerary_generation/day_facts.py"]

    resolver_source = (production / "day_content_resolver.py").read_text(encoding="utf-8")
    assert "return_visit_title_override" not in resolver_source

    for filename in (
        "day_intent.py",
        "title_brain.py",
        "day_intro_phrase_selection.py",
        "day_copy_qa.py",
    ):
        source = (production / filename).read_text(encoding="utf-8")
        assert "day_state" in source
