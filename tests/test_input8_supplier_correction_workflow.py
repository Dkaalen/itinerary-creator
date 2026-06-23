from itinerary_generation.input_review import build_structured_input_review, format_structured_input_review
from ui.input_review_panel import _review_table_rows


def test_input8_adds_correction_queue_labels_and_destination_confirmation():
    review = build_structured_input_review(
        [
            {
                "day": "Day 1",
                "type": "Hotel",
                "effective_type": "Hotel",
                "city": "Madeup Fjordtown",
                "hotel_name": "Fjord Hotel",
                "hotel_nights": "2",
                "room_category": "Standard double",
                "parser_confidence": 100,
                "parser_review_flags": [],
            },
            {
                "day": "Day 2",
                "type": "Criuse",
                "effective_type": "Cruise",
                "city": "Stavanger",
                "title": "Coastal cruise to Bergen",
                "route_origin": "Stavanger",
                "route_destination": "Bergen",
                "parser_confidence": 86,
                "parser_review_flags": [],
            },
        ]
    )

    unknown_destination = review.row_reviews[0]
    type_correction = review.row_reviews[1]

    assert unknown_destination.status == "Needs review"
    assert unknown_destination.review_priority == "Review"
    assert unknown_destination.destination_status == "Confirm destination"
    assert unknown_destination.next_action == "Confirm destination"
    assert unknown_destination.primary_fix == "Confirm destination spelling or add it to the registry."

    assert type_correction.confidence_label == "Medium"
    assert type_correction.next_action == "Accept type: Cruise"
    assert type_correction.primary_fix == "Review row type correction: Criuse → Cruise."

    text = format_structured_input_review(review)
    assert "Review queue: confirm before polishing" in text
    assert "Row 1 [Confirm destination]" in text
    assert "Row 2 [Accept type: Cruise]" in text


def test_input8_review_table_exposes_actionable_import_columns():
    review = build_structured_input_review(
        [
            {
                "day": "Day 1",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Bergen",
                "parser_confidence": 65,
                "parser_review_flags": ["missing_activity_title"],
            }
        ]
    )

    table = _review_table_rows(review)

    assert table[0]["Confidence"] == "65% · Low"
    assert table[0]["Priority"] == "Blocker"
    assert table[0]["Destination"] == "Known destination"
    assert table[0]["Next action"] == "Fill required field"
    assert table[0]["Primary fix"] == "Give this activity a clear client-facing title."
    assert table[0]["Missing fields"] == "Activity title"
