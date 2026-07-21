from __future__ import annotations

import json

import pytest

from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.state_serialization import calculator_state_from_json, calculator_state_to_json


def test_calculator_state_backup_round_trip_preserves_rows() -> None:
    state = CalculatorState(
        itinerary_name="Tromsø Northern Lights",
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                type="Activity",
                supplier="Guide Co",
                travel_element="Northern lights chase",
                gross_price_per_unit=1000,
                units=2,
                supplier_commission=0.15,
                supplier_currency="NOK",
                sales_price_per_unit=1400,
                sales_currency="NOK",
                comments="Warm clothing included",
            ),
        ),
    )

    restored = calculator_state_from_json(calculator_state_to_json(state))

    assert restored == state


def test_calculator_state_backup_assigns_missing_row_ids() -> None:
    payload = {
        "schema_version": 1,
        "kind": "booknordics_calculator_state",
        "itinerary_name": "Trip",
        "rows": [{"type": "Hotel", "travel_element": "Hotel stay"}],
    }

    restored = calculator_state_from_json(json.dumps(payload))

    assert restored.rows[0].row_id == "1"
    assert restored.rows[0].travel_element == "Hotel stay"


def test_calculator_state_backup_rejects_unknown_schema_version() -> None:
    payload = {
        "schema_version": 999,
        "kind": "booknordics_calculator_state",
        "rows": [],
    }

    with pytest.raises(ValueError, match="Unsupported calculator backup schema version"):
        calculator_state_from_json(json.dumps(payload))


def test_calculator_state_backup_round_trip_preserves_dashboard_pax() -> None:
    state = CalculatorState(itinerary_name="Group", number_of_pax=17, rows=(CalculatorRow(row_id="1"),))

    restored = calculator_state_from_json(calculator_state_to_json(state))

    assert restored.number_of_pax == 17
    assert json.loads(calculator_state_to_json(state))["schema_version"] == 2


def test_v1_calculator_backup_migrates_without_pax() -> None:
    payload = {
        "schema_version": 1,
        "kind": "booknordics_calculator_state",
        "itinerary_name": "Legacy",
        "rows": [{"row_id": "1", "travel_element": "Legacy row"}],
    }

    restored = calculator_state_from_json(json.dumps(payload))

    assert restored.number_of_pax is None
    assert restored.rows[0].travel_element == "Legacy row"


def test_calculator_backup_rejects_non_finite_numbers() -> None:
    state = CalculatorState(rows=(CalculatorRow(row_id="1", gross_price_per_unit=float("nan")),))

    with pytest.raises(ValueError):
        calculator_state_to_json(state)


def test_calculator_backup_normalizes_whole_number_pax_text() -> None:
    payload = {
        "schema_version": 2,
        "kind": "booknordics_calculator_state",
        "number_of_pax": "2.0",
        "rows": [],
    }

    restored = calculator_state_from_json(json.dumps(payload))

    assert restored.number_of_pax == 2


def test_calculator_backup_rejects_fractional_pax_without_truncating() -> None:
    payload = {
        "schema_version": 2,
        "kind": "booknordics_calculator_state",
        "number_of_pax": 2.5,
        "rows": [],
    }

    with pytest.raises(ValueError, match="positive integer"):
        calculator_state_from_json(json.dumps(payload))
