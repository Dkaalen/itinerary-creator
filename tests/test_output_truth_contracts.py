from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_leisure_writer import write_leisure_copy
from itinerary_generation.quality_gate import evaluate_client_output_quality
from itinerary_generation.render_model import RenderBlock, RenderDay, RenderDocument, RenderMetaLine, RenderSummary
from itinerary_generation.schedule_brain import build_day_schedule_profile
from itinerary_generation.schedule_time_ranges import parse_time_range


def _activity_rows(time_value: str):
    return [
        {"type": "Activity", "effective_type": "Activity", "city": "Reykjavík", "title": "Day Tour", "details": f"Time: {time_value}"},
        {"type": "Leisure", "city": "Reykjavík", "title": "Spend time at leisure"},
    ]


def test_time_range_contract_distinguishes_overnight_from_reversed_daytime():
    overnight = parse_time_range("6:30 pm - 1:30 am")
    reversed_daytime = parse_time_range("4:00 pm - 9:00 am")

    assert overnight.is_overnight is True
    assert overnight.end_minutes == 25 * 60 + 30
    assert reversed_daytime.is_invalid is True
    assert reversed_daytime.reason == "reversed_daytime_range"


def test_schedule_occupancy_blocks_false_free_time_after_full_day_tour():
    rows = _activity_rows("9:00 am - 7:00 pm")
    facts = build_day_facts(rows)
    profile = build_day_schedule_profile(rows)
    leisure = write_leisure_copy(facts, classify_day_intent(facts))

    assert profile.occupancy.is_full_day is True
    assert profile.occupancy.finishes_late is True
    assert leisure == "The arranged experience fills the day into the evening, so no additional plans are suggested."


def test_client_truth_gate_blocks_internal_copy_and_unsupported_overview_fact():
    document = RenderDocument(
        summary=RenderSummary(journey_arc=[{"chapter": "Stockholm", "days": "1", "experience": "Vasa Museum discovery"}]),
        days=[
            RenderDay(
                day="Day 1",
                number="1",
                city="Stockholm",
                title="Welcome to Stockholm",
                intro="Arrival in Stockholm.",
                blocks=[RenderBlock(kind="activity", title="City Walk", description="Generated without exposing raw supplier notes")],
            )
        ],
    )

    codes = {issue.code for issue in evaluate_client_output_quality(document).blocking_issues}

    assert "internal_copy_leak" in codes
    assert "unsupported_journey_overview_fact" in codes


def test_client_truth_gate_blocks_impossible_leisure_and_title_disagreement():
    document = RenderDocument(
        days=[
            RenderDay(
                day="Day 2",
                number="2",
                city="Reykjavík",
                title="Whale Watching",
                intro="A full day outside Reykjavík.",
                blocks=[
                    RenderBlock(kind="activity", title="Blue Lagoon Admission", meta=[RenderMetaLine("Time", "9:00 AM - 7:00 PM")], description="Blue Lagoon visit."),
                    RenderBlock(kind="leisure", section_title="Your Free Time", description="The rest of the day remains easy and flexible."),
                ],
            )
        ]
    )

    codes = {issue.code for issue in evaluate_client_output_quality(document).blocking_issues}

    assert "impossible_free_time_claim" in codes
    assert "day_activity_title_disagreement" in codes


def test_client_truth_gate_blocks_false_first_return_visit():
    document = RenderDocument(
        days=[RenderDay(day="Day 1", number="1", city="Rovaniemi", title="Return to Rovaniemi", intro="Back in Rovaniemi, settle into the hotel.")]
    )

    codes = {issue.code for issue in evaluate_client_output_quality(document).blocking_issues}

    assert "false_return_visit" in codes


def test_activity_intro_mode_requires_water_product_evidence():
    from itinerary_generation.copy.activity_composition import client_activity_intro

    photo_intro = client_activity_intro(
        "Photo Tour to Arctic Landscapes and Fjords",
        "Tromsø",
        "Scenic fjord safari by comfortable minivan with photography stops.",
    )
    road_intro = client_activity_intro(
        "Private Day Tour to Hardanger Fjords & Waterfalls",
        "Bergen",
        "Private vehicle, road stops and hotel pick-up.",
    )
    cruise_intro = client_activity_intro(
        "Silent Electric Fjord Cruise",
        "Bodø",
        "Sightseeing cruise aboard a silent electric ship.",
    )

    assert not photo_intro.startswith("Sail from")
    assert not road_intro.startswith("Sail from")
    assert cruise_intro.startswith("Sail from")


def test_full_leisure_intro_and_free_time_have_distinct_ownership():
    from itinerary_generation.day_intro_writer import write_day_intro

    rows = [{"type": "Leisure", "effective_type": "Leisure", "city": "Tromsø", "title": "Spend time at leisure"}]
    facts = build_day_facts(rows)
    intent = classify_day_intent(facts)

    assert write_day_intro(facts, intent) != write_leisure_copy(facts, intent)


def test_transport_endpoint_contract_rejects_service_phrase_as_origin():
    from itinerary_generation.transport_domain.route_summary import transport_endpoints_from_row

    assert transport_endpoints_from_row(
        {"type": "Transfer", "effective_type": "Transfer", "city": "Tromsø", "title": "Private transfer to Tromsø Airport"}
    ) == ("", "Tromsø Airport")


def test_activity_plus_overnight_train_title_is_departure_composition_not_false_arrival():
    from itinerary_generation.title_brain import plan_day_title_decision

    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Helsinki",
            "title": "A Finntastic Walking Tour in Helsinki",
            "original_title": "A Finntastic Walking Tour in Helsinki",
            "details": "Time: 1:30 PM - 3:45 PM",
        },
        {
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Helsinki",
            "title": "Self-arranged transfer to Helsinki Central Station",
        },
        {
            "type": "Train",
            "effective_type": "Train",
            "city": "Helsinki",
            "title": "Overnight Train Transfer with the Santa Claus Express to Rovaniemi",
            "details": "Helsinki to Rovaniemi - 11:13 PM - 10:59 AM",
        },
    ]

    decision = plan_day_title_decision(rows)

    assert decision.source == "activity_overnight_transport_composed_title"
    assert "Finntastic Walking Tour" in decision.text
    assert "Rovaniemi" in decision.text
    assert "Arrival in Rovaniemi" not in decision.text
