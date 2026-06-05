from itinerary_generation.transport_domain.model import build_transport_summary
from itinerary_generation.transport_domain.render import get_travel_arrangement_line as domain_travel_line
from itinerary_generation.transport_domain.titles import get_transport_route_phrase as domain_route_phrase
from itinerary_generation.transport_routes import get_route_points_for_transport as legacy_route_points
from itinerary_generation.transport_titles import get_transport_route_phrase as legacy_route_phrase
from itinerary_generation.travel_sequence_blocks import get_travel_arrangement_line as legacy_travel_line
from parser_modules.transport_titles import standardize_private_transfer_title
from itinerary_generation.transport_domain.parser import standardize_private_transfer_title as domain_private_transfer_title
from itinerary_generation.exclusion_sections import self_arranged_flight_notice
from itinerary_generation.transport_domain.exclusions import self_arranged_flight_notice as domain_flight_notice


def test_transport_domain_is_canonical_for_long_distance_coach_route():
    row = {
        "type": "Transfer",
        "effective_type": "Transport",
        "title": "Bus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Tromsø Busterminal Prostneset - Tickets Included",
        "details": "Final voucher timing will be released later",
        "city": "Tromsø",
    }

    summary = build_transport_summary(row)

    assert summary.row_type == "Transport"
    assert summary.route.origin == "Rovaniemi Bus Station"
    assert summary.route.destination == "Tromsø Busterminal Prostneset"
    assert summary.route.phrase == "Panoramic Coach Transfer from Rovaniemi Bus Station to Tromsø Busterminal Prostneset"
    assert summary.is_transport_like
    assert not summary.is_route_transfer


def test_legacy_transport_route_and_render_facades_delegate_to_domain():
    row = {
        "type": "Train",
        "title": "Train : Oslo to Bergen | 14:25 - 21:33 | Tickets Included",
        "details": "",
        "city": "Bergen",
        "includes": ["Tickets Included"],
    }

    assert legacy_route_points(row) == ("Oslo", "Bergen")
    assert legacy_route_phrase(row) == domain_route_phrase(row)
    assert legacy_travel_line(row) == domain_travel_line(row)
    assert legacy_travel_line(row).startswith("Scenic Train Transfer from Oslo to Bergen")


def test_parser_transport_title_facade_uses_domain_standardization():
    args = ("Private Airport to Hotel", "Private Airport to Hotel", "Helsinki")

    assert standardize_private_transfer_title(*args) == domain_private_transfer_title(*args)
    assert standardize_private_transfer_title(*args) == "Private transfer from Helsinki Airport to your accommodation"


def test_transport_exclusion_notice_uses_domain_flight_logic():
    row = {
        "type": "Flight",
        "title": "Flight Oslo to Bergen, self-arranged, cost not included",
        "commercial_status": "self_arranged",
    }

    assert self_arranged_flight_notice(row) == domain_flight_notice(row)
    assert self_arranged_flight_notice(row) == "Self-arranged flight to Bergen (not included)"
