from pathlib import Path
from tests.support.static_contracts import read_contract_text

from itinerary_generation.input_review import build_structured_input_review, format_structured_input_review
from ui.input_review_panel import _review_table_rows


def test_structured_review_builds_row_level_confidence_and_suggestions():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Oslo",
            "parser_confidence": 45,
            "parser_review_flags": ["missing_hotel_name", "missing_room_category"],
        },
        {
            "day": "Day 2",
            "type": "Criuse",
            "effective_type": "Cruise",
            "city": "Stavanger",
            "title": "Stavanger to Bergen coastal cruise",
            "route_origin": "Stavanger",
            "route_destination": "Bergen",
            "parser_confidence": 88,
            "parser_review_flags": [],
        },
        {
            "day": "Day 3",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Bergen",
            "title": "Walking tour",
            "parser_confidence": 100,
            "parser_review_flags": [],
        },
    ]

    review = build_structured_input_review(rows)

    assert review.average_confidence == 78
    assert review.low_confidence_count == 2
    assert review.suggested_fix_count == 2
    assert review.row_reviews[0].status == "Check before generation"
    assert review.row_reviews[0].confidence_label == "Low"
    assert review.row_reviews[0].review_priority == "Blocker"
    assert review.row_reviews[0].destination_status == "Known destination"
    assert review.row_reviews[0].next_action == "Fill required field"
    assert review.row_reviews[0].missing_fields == ("Hotel name", "Room category")
    assert "Add the hotel name" in review.row_reviews[0].suggested_fixes[0]
    assert review.row_reviews[1].status == "Needs review"
    assert review.row_reviews[1].confidence_label == "Medium"
    assert review.row_reviews[1].next_action == "Accept type: Cruise"
    assert "Criuse → Cruise" in review.row_reviews[1].suggested_fixes[0]
    assert review.row_reviews[2].status == "Ready"

    text = format_structured_input_review(review)
    assert "Rows needing review: 2" in text
    assert "Suggested fixes: 2" in text
    assert "Correction queue: blockers first" in text
    assert "Row 1 [Fill required field]" in text


def test_streamlit_review_table_is_import_review_not_debug_code():
    review = build_structured_input_review(
        [
            {
                "day": "Day 1",
                "type": "Transfer",
                "effective_type": "Transfer",
                "title": "Private transfer",
                "parser_confidence": 40,
                "parser_review_flags": ["missing_route_destination"],
            }
        ]
    )

    table = _review_table_rows(review)

    assert table == [
        {
            "Row": 1,
            "Day": "Day 1",
            "Type": "Transfer",
            "City / route": "Not detected",
            "Title": "Private transfer",
            "Confidence": "40% · Low",
            "Priority": "Blocker",
            "Status": "Check before generation",
            "Destination": "Not detected",
            "Next action": "Fill required field",
            "Primary fix": "Confirm from/to points for this transport row.",
            "Missing fields": "Route destination",
            "Review flags": "missing_route_destination",
        }
    ]


def test_ui_sources_expose_review_table_and_metrics():
    source = read_contract_text("ui/input_review_panel.py")
    model_source = read_contract_text("itinerary_generation/input_review.py")

    assert "st.dataframe" in source
    assert "Parser confidence" in source
    assert "Rows to review" in source
    assert source.count("st.expander(") == 1
    assert 'st.expander("Review summary"' not in source
    assert "StructuredInputRowReview" in model_source
    assert "build_input_row_reviews" in model_source
    assert "suggested_fixes" in model_source
    assert "review_priority" in model_source
    assert "Correction queue" in source
