from normalizer_modules.context import apply_contextual_travel_corrections, fill_missing_context_cities
from normalizer_modules.core import normalize_itinerary_rows
from normalizer_modules.rental import looks_like_rental_vehicle_row, normalize_rental_vehicle_row


def test_context_city_fill_stays_available_through_normalization():
    rows = normalize_itinerary_rows(
        [
            {"day": "Day 1", "type": "Arrival", "city": "Oslo", "title": "Arrival"},
            {"day": "Day 1", "type": "Activity", "city": "", "title": "Oslo Walking Tour"},
        ]
    )

    assert rows[1]["city"] == "Oslo"


def test_contextual_transfer_correction_keeps_arrival_transfer_direction():
    corrected = apply_contextual_travel_corrections(
        [
            {"day": "Day 3", "type": "Flight", "city": "Bergen", "title": "Flight Oslo to Bergen"},
            {"day": "Day 3", "type": "Transfer", "city": "Bergen", "title": "Private Hotel to Airport"},
            {"day": "Day 3", "type": "Hotel", "city": "Bergen", "title": "Hotel Bergen"},
        ]
    )

    assert corrected[1]["title"] == "Private transfer from Bergen Airport to your accommodation"


def test_contextual_overnight_train_uses_next_main_city():
    corrected = apply_contextual_travel_corrections(
        [
            {"day": "Day 2", "type": "Train", "city": "Helsinki", "title": "Overnight Train Transfer", "details": "overnight train"},
            {"day": "Day 3", "type": "Hotel", "city": "Rovaniemi", "title": "Hotel Aakenus"},
        ]
    )

    assert corrected[0]["title"] == "Overnight Train to Rovaniemi"


def test_fill_missing_context_cities_does_not_fill_transport_rows():
    filled = fill_missing_context_cities(
        [
            {"day": "Day 1", "type": "Arrival", "city": "Oslo", "title": "Arrival"},
            {"day": "Day 1", "type": "Transfer", "city": "", "title": "Oslo to Bergen"},
        ]
    )

    assert filled[1].get("city", "") == ""


def test_rental_helpers_are_isolated_from_core_normalization():
    row = {"type": "Hotel", "title": "Return your rental car at the airport"}

    assert looks_like_rental_vehicle_row(row)
    normalized = normalize_rental_vehicle_row(dict(row))
    assert normalized["type"] == "Car"
    assert normalized["effective_type"] == "Car"
    assert normalized["title"] == "Rental car return"
