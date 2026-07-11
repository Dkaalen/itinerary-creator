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


def test_time_range_contract_supports_24_hour_and_dotted_supplier_formats():
    standard = parse_time_range("Time: 09:00 - 19:00")
    dotted = parse_time_range("Time: 09.00 - 19.00")
    overnight = parse_time_range("18:00-01:00")

    assert (standard.start_minutes, standard.end_minutes, standard.source_format) == (9 * 60, 19 * 60, "24h")
    assert (dotted.start_minutes, dotted.end_minutes, dotted.source_format) == (9 * 60, 19 * 60, "24h_dotted")
    assert overnight.is_overnight is True
    assert overnight.end_minutes == 25 * 60


def test_schedule_occupancy_merges_overlapping_activity_intervals():
    rows = [
        {"type": "Activity", "effective_type": "Activity", "city": "Oslo", "title": "First tour", "time": "09:00 - 14:00"},
        {"type": "Activity", "effective_type": "Activity", "city": "Oslo", "title": "Second tour", "time": "10:00 - 15:00"},
    ]

    occupancy = build_day_schedule_profile(rows).occupancy

    assert occupancy.arranged_minutes == 6 * 60
    assert occupancy.arranged_span_minutes == 6 * 60
    assert occupancy.longest_gap_minutes == 0


def test_schedule_occupancy_blocks_false_free_time_after_full_day_tour():
    rows = _activity_rows("9:00 am - 7:00 pm")
    facts = build_day_facts(rows)
    profile = build_day_schedule_profile(rows)
    leisure = write_leisure_copy(facts, classify_day_intent(facts))

    assert profile.occupancy.is_full_day is True
    assert profile.occupancy.finishes_late is True
    assert leisure in {
        "The arranged experience fills the day into the evening, so no additional plans are suggested.",
        "Today’s included experience continues into the evening, leaving no meaningful space for extra plans.",
        "The schedule is occupied through the evening, so the day is best kept focused on the included experience.",
    }


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


def test_client_truth_gate_combines_activity_times_and_ignores_city_token_overlap():
    document = RenderDocument(
        days=[
            RenderDay(
                day="Day 3",
                number="3",
                city="Tromsø",
                title="Tromsø Whale Safari",
                intro="Two arranged experiences today.",
                blocks=[
                    RenderBlock(kind="activity", title="Tromsø Cable Car Ticket", meta=[RenderMetaLine("Time", "09:00 - 14:00")], description="Viewpoint visit."),
                    RenderBlock(kind="activity", title="Museum Visit", meta=[RenderMetaLine("Time", "14:00 - 19:00")], description="Museum visit."),
                    RenderBlock(kind="leisure", section_title="Your Free Time", description="The rest of the day remains easy and flexible."),
                ],
            )
        ]
    )

    codes = {issue.code for issue in evaluate_client_output_quality(document).blocking_issues}

    assert "impossible_free_time_claim" in codes


def test_client_truth_gate_blocks_malformed_titles_duplicate_blocks_and_destination_conflicts():
    duplicate = RenderBlock(kind="leisure", section_title="Your Free Time", description="Open time in Oslo is flexible.")
    document = RenderDocument(
        days=[
            RenderDay(
                day="Day 4",
                number="4",
                city="Alta",
                title="Departure from Oslo - ?",
                intro="Departure arrangements.",
                blocks=[duplicate, RenderBlock(kind="leisure", section_title="Your Free Time", description="Open time in Oslo is flexible.")],
            )
        ]
    )

    codes = {issue.code for issue in evaluate_client_output_quality(document).blocking_issues}

    assert "malformed_client_title" in codes
    assert "day_destination_title_disagreement" in codes
    assert "duplicate_rendered_block" in codes


def test_client_truth_gate_detects_unlisted_unsupported_named_overview_fact():
    document = RenderDocument(
        summary=RenderSummary(journey_arc=[{"chapter": "Copenhagen", "days": "1", "experience": "Rosenborg Castle discovery"}]),
        days=[RenderDay(day="Day 1", number="1", city="Copenhagen", title="Welcome to Copenhagen", intro="Arrival and hotel check-in.")],
    )

    codes = {issue.code for issue in evaluate_client_output_quality(document).blocking_issues}

    assert "unsupported_journey_overview_fact" in codes


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


def test_airport_transfer_contract_reports_conflicting_direction_instead_of_guessing():
    from itinerary_generation.airport_transfer_contract import airport_transfer_facts

    facts = airport_transfer_facts(
        {
            "title": "Private transfer to Oslo Airport",
            "details": "On arrival, transfer from the airport to the hotel.",
        }
    )

    assert facts.is_airport_transfer is True
    assert facts.direction == "unknown"
    assert facts.evidence.startswith("conflicting_direction:")


def test_whale_description_uses_activity_city_instead_of_fixed_reykjavik_copy():
    from itinerary_generation.activity_description_helpers import get_activity_description

    description = get_activity_description(
        {
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Akureyri",
            "title": "Whale Watching from Downtown",
            "original_title": "Whale Watching from Downtown",
            "details": "Whale watching boat tour from Akureyri harbour.",
        }
    )

    assert "Akureyri" in description
    assert "Reykjavík" not in description


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


def test_real_output_scorer_preserves_blocking_truth_gate_severity():
    from types import SimpleNamespace

    from scripts.real_output_qa.scoring import _score_client_truth_contracts

    document = RenderDocument(
        days=[
            RenderDay(
                day="Day 1",
                number="1",
                city="Alta",
                title="Departure from Oslo - ?",
                intro="Departure arrangements.",
            )
        ]
    )
    issues = []

    _score_client_truth_contracts(issues, SimpleNamespace(render_document=document), [])

    assert any(issue.code == "malformed_client_title" and issue.severity == "error" for issue in issues)
    assert any(issue.code == "day_destination_title_disagreement" and issue.severity == "error" for issue in issues)


def test_destination_profile_overview_copy_requires_source_evidence():
    from itinerary_generation.journey_overview_evidence import chapter_experience

    rovaniemi_rows = [
        {"type": "Arrival", "effective_type": "Arrival", "city": "Rovaniemi", "title": "Arrival in Rovaniemi"},
        {"type": "Hotel", "effective_type": "Hotel", "city": "Rovaniemi", "title": "Hotel stay in Rovaniemi"},
        {"type": "Leisure", "effective_type": "Leisure", "city": "Rovaniemi", "title": "A day at leisure in Rovaniemi"},
    ]
    alesund_rows = [
        {"type": "Flight", "effective_type": "Flight", "city": "Ålesund", "title": "Flight to Ålesund"},
        {"type": "Activity", "effective_type": "Activity", "city": "Ålesund", "title": "Geiranger"},
    ]

    rovaniemi = chapter_experience(rovaniemi_rows, "Rovaniemi")
    alesund = chapter_experience(alesund_rows, "Ålesund")

    assert "Lapland" not in rovaniemi
    assert "Arctic Circle" not in rovaniemi
    assert rovaniemi == "Arrival and independent time in Rovaniemi"
    assert "Art Nouveau" not in alesund
    assert alesund == "Geiranger"


def test_open_activity_slot_is_treated_as_placeholder_not_arranged_experience():
    from itinerary_generation.day_leisure_facts import is_blank_activity_or_leisure

    row = {
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Reykjavík",
        "title": "Open slot for activity",
    }

    assert is_blank_activity_or_leisure(row) is True
    assert build_day_facts([row]).has_activity is False
