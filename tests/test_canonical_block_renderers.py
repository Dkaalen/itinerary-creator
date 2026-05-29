from ui.canonical_blocks import render_activity_block, render_accommodation_block
from ui.day_blocks import build_activity_block, build_accommodation_block


def test_extracted_activity_renderer_matches_existing_day_block_renderer():
    row = {
        "row_id": "activity-1",
        "type": "Activity",
        "effective_type": "Activity",
        "title": "Museum Visit",
        "original_title": "Museum Visit",
        "details": "Museum Visit",
        "time": "10:00 AM",
        "duration": "2 hours",
        "includes": ["Admission ticket", "Local guide"],
    }

    assert render_activity_block(row) == build_activity_block(row)


def test_extracted_accommodation_renderer_matches_existing_day_block_renderer():
    row = {
        "row_id": "hotel-1",
        "type": "Hotel",
        "effective_type": "Hotel",
        "title": "Hotel Bergen",
        "hotel_name": "Hotel Bergen",
        "city": "Bergen",
        "hotel_nights": "2",
        "room_category": "Standard Double Room",
        "meal_plan": "breakfast",
    }

    assert render_accommodation_block(row) == build_accommodation_block(row)
