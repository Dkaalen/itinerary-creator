from itinerary_generation.canonical_builder import canonical_accommodation_block


def test_accommodation_does_not_add_or_similar_by_default():
    row = {
        "row_id": "hotel-arthur",
        "type": "Hotel",
        "effective_type": "Hotel",
        "title": "Hotel Arthur",
        "hotel_name": "Hotel Arthur",
        "city": "Copenhagen",
        "hotel_nights": "2",
        "room_category": "Standard Double Room",
        "meal_plan": "breakfast",
    }

    block = canonical_accommodation_block(row)

    assert "or similar" not in block.title.lower()
    assert block.title == "Hotel Arthur in Copenhagen for 2 nights"


def test_accommodation_keeps_or_similar_when_present_in_input():
    row = {
        "row_id": "hotel-similar",
        "type": "Hotel",
        "effective_type": "Hotel",
        "title": "Hotel Arthur or similar",
        "hotel_name": "Hotel Arthur",
        "details": "Hotel Arthur or similar",
        "city": "Copenhagen",
        "hotel_nights": "2",
        "room_category": "Standard Double Room",
        "meal_plan": "breakfast",
    }

    block = canonical_accommodation_block(row)

    assert "Hotel Arthur or similar" in block.title
    assert block.title == "Hotel Arthur or similar in Copenhagen for 2 nights"
