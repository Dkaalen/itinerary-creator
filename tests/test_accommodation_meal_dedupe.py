from itinerary_generation.canonical_builder import canonical_accommodation_block


def test_accommodation_meal_not_repeated_when_already_in_inclusions():
    row = {
        "row_id": "hotel-1",
        "type": "Hotel",
        "effective_type": "Hotel",
        "city": "Saariselkä",
        "hotel_name": "Kakslauttanen Arctic Resort",
        "hotel_nights": "2",
        "room_category": "Glass igloo",
        "meal_plan": "Breakfast and dinner",
        "includes": ["Breakfast and dinner included"],
        "details": "Accommodation includes breakfast and dinner.",
    }

    block = canonical_accommodation_block(row)

    assert block.title == "Kakslauttanen Arctic Resort in Saariselkä for 2 nights"
    assert block.lines == ["Room category: Glass Igloo"]


def test_accommodation_meal_shown_when_not_already_listed():
    row = {
        "row_id": "hotel-2",
        "type": "Hotel",
        "effective_type": "Hotel",
        "city": "Bergen",
        "hotel_name": "Example Hotel",
        "hotel_nights": "1",
        "room_category": "Standard Room",
        "meal_plan": "Breakfast",
        "includes": [],
        "details": "",
    }

    block = canonical_accommodation_block(row)

    assert block.lines == ["Room category: Standard Room, breakfast included"]
