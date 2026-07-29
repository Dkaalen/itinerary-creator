from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app_modules.saved_project_builder import build_saved_project_from_state, hash_source_input
from app_modules.saved_project_constants import SAVED_PROJECT_SCHEMA_VERSION
from app_modules.saved_project_serialization import saved_project_from_dict, saved_project_to_dict, saved_project_to_json
from app_modules.saved_project_validation import SavedProjectError, validate_saved_project_payload


def _clock() -> datetime:
    return datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _generated_state() -> dict:
    return {
        "last_generated_raw_text": "Day 1\tActivity\tOslo Fjord Cruise",
        "raw_text_input": "stale raw input should not be preferred",
        "parsed_rows": [
            {"day": "Day 1", "row_id": "row-1", "type": "Activity", "title": "Oslo Fjord Cruise"},
        ],
        "output_edits": {
            "output_brand": "booknordics_customer",
            "detail_level": "Rich descriptive",
            "day_page_layout": "classic",
            "trip_title": "Norway Winter Group",
            "days": {"Day 1": {"intro": "Manual intro"}},
            "rows": {"row-1": {"title": "Edited cruise"}},
            "cover_image": {"mode": "manual", "path": "images/cover.jpg", "crop_focus": "center", "data_uri": "data:image/png;base64,AAA"},
            "summary_image": {"mode": "none", "path": "", "crop_focus": "top", "auto_data_uri": "data:image/png;base64,BBB"},
            "day_images": {
                "Day 1": {
                    "mode": "manual",
                    "path": "images/oslo.jpg",
                    "crop_focus": "bottom",
                    "upload": {"data_uri": "data:image/png;base64,CCC"},
                }
            },
            "pictures_added": True,
        },
        "detail_level": "Rich descriptive",
        "day_page_layout": "classic",
        "pdf_status": "Needs refresh",
        "itinerary_html": "<html>must not be saved</html>",
        "pdf_bytes": b"%PDF",
        "_visual_editor_commit_nonce": "temporary",
        "day_image_matches": {"Day 1": {"data_uri": "data:image/png;base64,DDD"}},
    }


def test_saved_project_can_be_created_from_generated_state_without_session_dump() -> None:
    project = build_saved_project_from_state(_generated_state(), itinerary_name="Norway Winter Group", project_id="project-1", clock=_clock)
    payload = saved_project_to_dict(project)

    assert payload["saved_schema_version"] == SAVED_PROJECT_SCHEMA_VERSION
    assert payload["kind"] == "itinerary_project"
    assert payload["metadata"]["project_id"] == "project-1"
    assert payload["metadata"]["itinerary_name"] == "Norway Winter Group"
    assert payload["metadata"]["created_at"] == "2026-01-02T03:04:05Z"
    assert payload["source"]["source_input"] == "Day 1\tActivity\tOslo Fjord Cruise"
    assert payload["source"]["source_hash"] == hash_source_input(payload["source"]["source_input"])
    assert payload["output_brand"] == "booknordics_customer"
    assert payload["mode"] == "booknordics_customer"
    assert payload["generated_baseline_snapshot"] == payload["current_snapshot"]

    encoded = json.dumps(payload)
    assert "itinerary_html" not in encoded
    assert "pdf_bytes" not in encoded
    assert "_visual_editor_commit_nonce" not in encoded
    assert "day_image_matches" not in encoded
    assert "data:image" not in encoded


def test_saved_project_preserves_compact_image_edit_state() -> None:
    payload = saved_project_to_dict(build_saved_project_from_state(_generated_state(), clock=_clock))

    assert payload["image_state"] == {
        "cover_image": {"mode": "manual", "path": "images/cover.jpg", "crop_focus": "center"},
        "summary_image": {"mode": "none", "path": "", "crop_focus": "top"},
        "day_images": {"Day 1": {"mode": "manual", "path": "images/oslo.jpg", "crop_focus": "bottom"}},
        "pictures_added": True,
    }
    assert payload["current_snapshot"]["output_edits"]["day_images"] == payload["image_state"]["day_images"]


def test_saved_project_serialization_round_trip() -> None:
    project = build_saved_project_from_state(_generated_state(), itinerary_name="Round trip", clock=_clock)
    payload_json = saved_project_to_json(project)
    restored = saved_project_from_dict(json.loads(payload_json))

    assert saved_project_to_dict(restored) == json.loads(payload_json)


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (lambda payload: payload.pop("current_snapshot"), "missing required fields"),
        (lambda payload: payload.__setitem__("saved_schema_version", 999), "Unsupported saved project schema version"),
        (lambda payload: payload["metadata"].__setitem__("status", "deleted"), "status is not supported"),
        (lambda payload: payload["current_snapshot"].__setitem__("output_edits", []), "output edit objects"),
        (lambda payload: payload.__setitem__("itinerary_html", "<html>bad</html>"), "temporary or preview-only fields"),
    ],
)
def test_saved_project_validation_fails_safely(mutation, expected: str) -> None:
    payload = saved_project_to_dict(build_saved_project_from_state(_generated_state(), clock=_clock))
    mutation(payload)

    with pytest.raises(SavedProjectError, match=expected):
        validate_saved_project_payload(payload)


def test_saved_project_payload_size_guard() -> None:
    payload = saved_project_to_dict(build_saved_project_from_state(_generated_state(), clock=_clock))
    payload["current_snapshot"]["output_edits"]["huge_note"] = "x" * 500

    with pytest.raises(SavedProjectError, match="payload is too large"):
        validate_saved_project_payload(payload, max_bytes=100)


def test_saved_project_round_trip_preserves_current_calculator_snapshot() -> None:
    from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY, CURRENCY_RATES_STATE_KEY
    from calculator.calculator_state import CalculatorState
    from calculator.row_model import CalculatorRow

    state = _generated_state()
    state[CALCULATOR_STATE_KEY] = CalculatorState(
        itinerary_name="Calculator Group",
        number_of_pax=21,
        trip_start_date="2026-02-01",
        rows=(
            CalculatorRow(
                row_id="1",
                travel_element="Oslo hotel",
                gross_price_per_unit=100,
                units=2,
                supplier_currency="EUR",
                sales_currency="NOK",
                from_date="01.02.2026",
                from_date_mode="linked",
                from_date_offset=0,
                to_date="05.02.2026",
                to_date_mode="locked",
            ),
        ),
    )
    state[CURRENCY_RATES_STATE_KEY] = {"NOK": 1, "EUR": 12.5}

    payload_json = saved_project_to_json(build_saved_project_from_state(state, clock=_clock))
    restored = saved_project_from_dict(json.loads(payload_json))
    snapshot = restored.calculator_snapshot

    assert snapshot.schema_version == 4
    assert snapshot.number_of_pax == 21
    assert snapshot.trip_start_date == "2026-02-01"
    assert snapshot.rows[0]["travel_element"] == "Oslo hotel"
    assert snapshot.rows[0]["from_date_mode"] == "linked"
    assert snapshot.rows[0]["from_date_offset"] == 0
    assert snapshot.rows[0]["to_date_mode"] == "locked"
    assert snapshot.currency_rates["EUR"] == 12.5


def test_saved_project_validation_rejects_invalid_calculator_currency_rate() -> None:
    payload = saved_project_to_dict(build_saved_project_from_state(_generated_state(), clock=_clock))
    payload["calculator_snapshot"]["currency_rates"]["EUR"] = 0

    with pytest.raises(SavedProjectError, match="currency rates must be positive"):
        validate_saved_project_payload(payload)


def test_saved_project_validation_rejects_malformed_calculator_rows() -> None:
    payload = saved_project_to_dict(build_saved_project_from_state(_generated_state(), clock=_clock))
    payload["calculator_snapshot"]["rows"] = [{"row_id": "1", "gross_price_per_unit": float("nan")}]

    with pytest.raises(SavedProjectError, match="must be finite"):
        validate_saved_project_payload(payload)


def test_saved_project_validation_rejects_non_object_calculator_rows() -> None:
    payload = saved_project_to_dict(build_saved_project_from_state(_generated_state(), clock=_clock))
    payload["calculator_snapshot"]["rows"] = ["broken row"]

    with pytest.raises(SavedProjectError, match="rows must contain objects"):
        validate_saved_project_payload(payload)
