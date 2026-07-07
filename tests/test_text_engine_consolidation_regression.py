from __future__ import annotations

from types import SimpleNamespace

from generator import create_day_intro, create_journey_arc, group_rows_by_day
from itinerary_generation.client_text_decisions import (
    client_activity_intro,
    client_group_tour_intro,
    sanitize_journey_arc_phrase,
)
from itinerary_generation.quality_gate import evaluate_client_output_quality


def test_activity_intro_uses_same_shared_decision_for_standalone_and_mixed_days():
    activity = {
        "day": "Day 1",
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Oslo",
        "title": "Oslo Walking Tour",
        "details": "Guided walking tour through central Oslo",
    }
    transfer = {
        "day": "Day 1",
        "type": "Transfer",
        "effective_type": "Transfer",
        "city": "Oslo",
        "title": "Private Hotel to City Centre",
        "details": "Private transfer in Oslo",
    }
    expected = client_activity_intro("Oslo Walking Tour", "Oslo", activity["details"])

    assert create_day_intro([activity]) == expected
    assert expected in create_day_intro([activity, transfer])


def test_group_tour_intro_uses_shared_decision_engine():
    supplier_activity = {
        "day": "Day 2",
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Vik",
        "title": "South Coast and Katla Ice Cave",
        "details": "Day 2: South Coast and Katla Ice Cave. Visit waterfalls, black-sand scenery and the Katla Ice Cave.",
    }

    assert create_day_intro([supplier_activity]) == client_group_tour_intro(
        "South Coast and Katla Ice Cave",
        "Vik",
        supplier_activity["details"],
    )


def test_journey_arc_uses_destination_logistics_rule_instead_of_connection_filler():
    rows = [
        {
            "day": "Day 8",
            "type": "Flight",
            "effective_type": "Flight",
            "city": "Bergen",
            "title": "Flight Tromsø to Bergen",
            "details": "Self-arranged flight from Tromsø to Bergen",
        },
        {
            "day": "Day 8",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Bergen",
            "title": "Hotel in Bergen",
            "details": "1 night, breakfast included",
        },
    ]

    arc = create_journey_arc(group_rows_by_day(rows))

    assert arc == [{"chapter": "Bergen", "days": "8", "experience": "Welcome to Bergen"}]


def test_journey_arc_keeps_real_scenic_route_when_that_is_the_meaningful_context():
    rows = [
        {
            "day": "Day 9",
            "type": "Transport",
            "effective_type": "Transport",
            "city": "Oslo",
            "title": "Norway in a Nutshell to Oslo",
            "details": "Norway in a Nutshell from Bergen to Oslo with Bergen Railway, Flåm Railway and fjord cruise",
        },
        {
            "day": "Day 9",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Oslo",
            "title": "Hotel in Oslo",
            "details": "2 nights, breakfast included",
        },
    ]

    arc = create_journey_arc(group_rows_by_day(rows))

    assert arc[0]["experience"] == "Norway in a Nutshell and scenic rail"


def test_client_quality_gate_uses_meaning_based_journey_arc_check():
    render_document = SimpleNamespace(
        summary=SimpleNamespace(
            journey_arc=[
                {"chapter": "Bergen", "days": "8", "experience": "Continue your journey with arranged travel connected"}
            ]
        ),
        days=[],
        final_sections=[],
    )

    report = evaluate_client_output_quality(render_document)

    assert "weak_journey_arc_meaning" in {issue.code for issue in report.blocking_issues}


def test_shared_journey_arc_sanitizer_is_not_phrase_specific_whack_a_mole():
    assert sanitize_journey_arc_phrase("Flight connection", chapter="Bergen") == "Welcome to Bergen"
    assert sanitize_journey_arc_phrase("Onward train", chapter="Rovaniemi") == "Welcome to Rovaniemi"
    assert sanitize_journey_arc_phrase("Aurora experience", chapter="Tromsø") == "Northern Lights experience"
