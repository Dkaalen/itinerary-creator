from itinerary_generation.transport_domain.route_points import get_route_points_for_transport


def test_canonical_route_fields_beat_weaker_city_and_title_inference() -> None:
    row = {
        "effective_type": "Drive",
        "type": "Drive",
        "city": "Flåm",
        "title": "Drive to Bergen",
        "details": "Self transfer to the car rental office before driving to Bergen.",
        "route_origin": "Oslo",
        "route_destination": "Bergen",
    }

    assert get_route_points_for_transport(row) == ("Oslo", "Bergen")


def test_route_text_inference_remains_available_without_canonical_fields() -> None:
    row = {
        "effective_type": "Drive",
        "type": "Drive",
        "city": "Flåm",
        "title": "Drive to Bergen",
    }

    assert get_route_points_for_transport(row) == ("Flåm", "Bergen")


def test_action_prose_in_canonical_origin_falls_back_to_row_city() -> None:
    row = {
        "effective_type": "Drive",
        "type": "Drive",
        "city": "Reykjavík",
        "title": "Drive the Golden Circle to Asborgir",
        "route_origin": "Drive the Golden Circle",
        "route_destination": "Asborgir",
    }

    assert get_route_points_for_transport(row) == ("Reykjavík", "Asborgir")
