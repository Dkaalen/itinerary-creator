from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.date_resolver import get_trip_date_range_text
from itinerary_generation.summaries_experience import describe_city_experience
from itinerary_generation.transport_domain.render_arrangements import get_travel_arrangement_line
from normalizer_modules.hotel_row import normalize_hotel_row
from text_polish import format_duration_display, polish_client_text


def test_cross_year_cover_uses_ordered_day_dates_not_stray_maximum_year():
    rows = [
        {"day": "Day 1", "start_date": "21.12.2026"},
        {"day": "Day 16", "start_date": "05.01.2028"},
        {"day": "Day 17", "start_date": "06.01.2027"},
    ]
    assert get_trip_date_range_text(rows) == "21st of December 2026 - 6th of January 2027"


def test_flight_route_and_luggage_are_client_ready():
    row = {
        "type": "Flight", "effective_type": "Flight", "city": "Tromsø",
        "title": "Flight to Svolvær", "time": "5:15 pm - 6:10 pm",
        "details": "Tromsø: Flight to Svolvær - Time: 5:15 pm - 6:10 pm - Luggage included: 1 x 23 kg check in and 1 x 8 kg carry on per person",
    }
    assert get_travel_arrangement_line(row) == (
        "Flight from Tromsø to Svolvær — 5:15 PM - 6:10 PM; Includes: "
        "Flight tickets, 1 x 23 kg checked bag, 1 x 8 kg carry-on bag per person"
    )


def test_hotel_bed_configuration_preserves_all_beds_without_duplicate_double():
    row = normalize_hotel_row({
        "city": "Tromsø", "hotel_name": "Quality Grand Tromso Hotel",
        "room_category": "1 x Family room", "details": "1 x Family room - Double bed, Bunk bed - Breakfast included",
        "hotel_nights": "5", "meal_plan": "breakfast", "start_date": "21.12.2026", "end_date": "26.12.2026",
    })
    assert row["room_category"] == "1 x Family Room - double bed and bunk bed"


def test_placeholder_meeting_point_is_not_rendered():
    block = canonical_activity_block({
        "type": "Activity", "effective_type": "Activity", "city": "Kiruna",
        "title": "Northern Lights Hunt", "meeting_point": "x", "includes": ["Guide"],
    })
    assert all(line.value.lower() != "x" for line in block.meta)


def test_common_supplier_typos_are_repaired():
    assert polish_client_text("alonside the sea; warm drinkgs") == "alongside the sea; warm drinks"


def test_lofoten_summary_does_not_invent_trollfjord():
    rows = [{"type": "Activity", "effective_type": "Activity", "city": "Svolvær", "title": "Photo Tour to Reine and Haukland Beach", "details": "Lofoten scenery"}]
    phrase = describe_city_experience(rows)
    assert "Trollfjord" not in phrase


def test_standalone_hyphenated_hour_duration_is_client_ready():
    assert format_duration_display("3-hour") == "3 hours"
    assert format_duration_display("8-hour") == "8 hours"
