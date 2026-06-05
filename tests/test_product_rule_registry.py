from itinerary_generation.activity_description_helpers import get_activity_description
from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.product_rules import find_product_match, product_warning
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.titles import create_client_activity_title
from generator import group_rows_by_day


def test_tromso_round_trip_ticket_is_weak_product_match_not_fjellheisen():
    row = {
        "row_id": "viewpoint-ticket",
        "type": "Activity",
        "effective_type": "Activity",
        "day": "Day 1",
        "city": "Tromsø",
        "title": "Round Trip Ticket",
        "original_title": "Tromsø: Round Trip Ticket",
        "details": "Enjoy the spectacular view of Tromsø and its beautiful surroundings from above.",
    }

    match = find_product_match(row)

    assert match is not None
    assert match.rule_id == "tromso_viewpoint_ticket_possible_fjellheisen"
    assert match.is_weak
    assert match.title == "Round-trip viewpoint ticket in Tromsø"
    assert "Fjellheisen" not in match.title
    assert "Fjellheisen" not in match.description
    assert product_warning(row)[0] == "ambiguous_activity_title"
    assert create_client_activity_title(row) == "Round-trip viewpoint ticket in Tromsø"

    block = canonical_activity_block(row)
    assert block.title == "Round-trip viewpoint ticket in Tromsø"
    assert "ambiguous_activity_title" in block.warnings


def test_explicit_tromso_cable_car_can_use_fjellheisen_title():
    row = {
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Tromsø",
        "title": "Round trip cable car ticket to the mountain viewpoint",
        "details": "Tromsø cable car round-trip ticket with flexible timing.",
    }

    match = find_product_match(row)

    assert match is not None
    assert match.rule_id == "fjellheisen"
    assert match.is_strong
    assert match.title == "Fjellheisen Cable Car"
    assert create_client_activity_title(row) == "Fjellheisen Cable Car"


def test_registry_owns_munch_tallinn_nutshell_and_korouoma_rules():
    munch = {"type": "Activity", "city": "Oslo", "title": "Tickets to the Munch Museum"}
    assert find_product_match(munch).rule_id == "munch_museum"
    assert create_client_activity_title(munch) == "Munch Museum Visit"
    assert "Munch Museum" in get_activity_description(munch)

    old_town = {
        "type": "Activity",
        "city": "Tallinn",
        "title": "Tallinn Old Town Guided Tour",
        "details": "Guided walking tour through Old Town Tallinn.",
    }
    assert find_product_match(old_town).rule_id == "tallinn_old_town_guided_tour"
    assert create_client_activity_title(old_town) == "Old Town Guided Tour"

    ferry = {
        "type": "Activity",
        "city": "Helsinki",
        "title": "Excursion to Tallinn",
        "details": "Departure from Helsinki: 10:30 am - Return from Tallinn: 7:30 pm - Ferry tickets included.",
    }
    assert find_product_match(ferry).rule_id == "tallinn_ferry_framework"
    assert create_client_activity_title(ferry) == "Day Excursion to Tallinn"

    nutshell = {
        "type": "Activity",
        "city": "Bergen",
        "title": "Nærøyfjord Cruise & Luggage Transfer Bergen to Oslo: Day Tour incl. the Flåm Train",
        "details": "Norway in a Nutshell Bergen to Oslo with fjord cruise and Flåm Railway.",
    }
    assert find_product_match(nutshell).rule_id == "norway_in_a_nutshell"
    assert create_client_activity_title(nutshell) == "Norway in a Nutshell from Bergen to Oslo"

    korouoma = {"type": "Activity", "city": "Rovaniemi", "title": "Korouoma Frozen Waterfalls Hike & BBQ"}
    assert find_product_match(korouoma).rule_id == "korouoma_canyon"
    assert "Korouoma Canyon" in get_activity_description(korouoma)


def test_structured_document_uses_registry_warning_for_weak_product_match():
    rows = [
        {
            "row_id": "weak-ticket",
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Tromsø",
            "title": "Round-trip viewpoint ticket in Tromsø",
            "original_title": "Tromsø: Round Trip Ticket",
            "details": "Enjoy the spectacular view of Tromsø and its beautiful surroundings from above.",
        }
    ]

    doc = build_itinerary_document(rows, group_rows_by_day(rows))
    warning_codes = {warning.code for warning in doc.warnings}

    assert "ambiguous_activity_title" in warning_codes
