from pathlib import Path

from itinerary_generation.input_review import (
    apply_input_correction_actions,
    build_input_correction_actions,
    build_structured_input_review,
    format_structured_input_review,
)
from ui.input_review_panel import _correction_action_rows


def test_input9_builds_safe_accept_actions_for_parser_type_corrections():
    rows = [
        {
            "day": "Day 7",
            "type": "Criuse",
            "effective_type": "Cruise",
            "city": "Stavanger",
            "title": "Atlantic Coastal Cruise Transfer to Bergen",
            "parser_confidence": 88,
            "parser_review_flags": [],
        }
    ]

    review = build_structured_input_review(rows)

    assert len(review.correction_actions) == 1
    action = review.correction_actions[0]
    assert action.row_number == 1
    assert action.safe_auto_apply is True
    assert action.field_updates == {"type": "Cruise"}
    assert action.action_label == "Accept parser fix: type Criuse → Cruise"

    text = format_structured_input_review(review)
    assert "Acceptable parser fixes: 1" in text
    assert "Safe parser fixes ready" in text
    assert "Row 1: Accept parser fix: type Criuse → Cruise" in text


def test_input9_applies_safe_parser_corrections_without_touching_human_review_rows():
    rows = [
        {
            "day": "Day 7",
            "type": "Criuse",
            "effective_type": "Cruise",
            "city": "Stavanger",
            "parser_confidence": 88,
            "parser_review_flags": [],
        },
        {
            "day": "Day 8",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Unknown Fjordtown",
            "parser_confidence": 82,
            "parser_review_flags": [],
        },
    ]

    corrected_rows, applied = apply_input_correction_actions(rows)

    assert len(applied) == 1
    assert corrected_rows[0]["type"] == "Cruise"
    assert corrected_rows[0]["accepted_input_corrections"] == ["Accept parser fix: type Criuse → Cruise"]
    assert corrected_rows[1]["type"] == "Activity"
    assert "accepted_input_corrections" not in corrected_rows[1]


def test_input9_correction_table_is_user_actionable_not_debug_payload():
    review = build_structured_input_review(
        [
            {
                "day": "Day 7",
                "type": "Crusie",
                "effective_type": "Cruise",
                "city": "Bergen",
                "parser_confidence": 86,
                "parser_review_flags": [],
            }
        ]
    )

    table = _correction_action_rows(review)

    assert table == [
        {
            "Row": 1,
            "Action": "Accept parser fix: type Crusie → Cruise",
            "Fields updated": "type",
            "Safe": "Yes",
            "Reason": "Parser-normalized row type or destination alias can be accepted safely.",
        }
    ]


def test_input9_ui_exposes_single_accept_button_without_nested_expanders():
    source = Path("ui/input_review_panel.py").read_text(encoding="utf-8")
    model_source = Path("itinerary_generation/input_review.py").read_text(encoding="utf-8")

    assert source.count("st.expander(") == 1
    assert "Accept safe parser fixes" in source
    assert "apply_input_correction_actions" in source
    assert "StructuredInputCorrectionAction" in model_source
    assert "build_input_correction_actions" in model_source
