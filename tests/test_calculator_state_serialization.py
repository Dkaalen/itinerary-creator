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
