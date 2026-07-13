from __future__ import annotations

import pytest

from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.validation import CalculatorValidationError, ensure_valid_calculator_state, validate_calculator_state


def test_validation_rejects_missing_rate_invalid_commission_and_duplicate_ids() -> None:
    state = CalculatorState(
        rows=(
            CalculatorRow(row_id="1", supplier_currency="XYZ", sales_currency="NOK", supplier_commission=1.2),
            CalculatorRow(row_id="1", supplier_currency="NOK", sales_currency="NOK"),
        )
    )

    issues = validate_calculator_state(state)

    assert {issue.code for issue in issues} == {"duplicate_row_id", "invalid_commission", "missing_exchange_rate"}
    with pytest.raises(CalculatorValidationError):
        ensure_valid_calculator_state(state)


def test_validation_accepts_unknown_currency_with_positive_manual_rate() -> None:
    state = CalculatorState(
        number_of_pax=2,
        rows=(
            CalculatorRow(
                row_id="1",
                supplier_currency="XYZ",
                supplier_x_rate_override=4.25,
                sales_currency="NOK",
            ),
        ),
    )

    assert validate_calculator_state(state) == ()
