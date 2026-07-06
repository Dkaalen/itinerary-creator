from __future__ import annotations

from app_modules.calculator_grid_values import (
    currency_or_default,
    field_value,
    formula_override_value,
    percent_to_decimal,
    row_has_no_user_values,
)
from calculator.defaults import DEFAULT_CALCULATOR_CURRENCY
from calculator.row_model import CalculatorRow


def test_calculator_grid_values_convert_percent_fields_for_formula_storage() -> None:
    assert field_value("supplier_commission", "12") == 0.12
    assert field_value("supplier_commission", "12%") == 0.12
    assert percent_to_decimal(0) == 0.0


def test_calculator_grid_values_keep_blank_formula_overrides_empty() -> None:
    assert formula_override_value("profit_override", "") is None
    assert formula_override_value("profit_override", "null") is None
    assert formula_override_value("gp_percent", "10") == 0.10


def test_calculator_grid_values_normalize_currency_and_blank_rows() -> None:
    assert currency_or_default("") == DEFAULT_CALCULATOR_CURRENCY
    assert currency_or_default("eur") == "EUR"
    assert row_has_no_user_values(CalculatorRow(row_id="1")) is True
    assert row_has_no_user_values(CalculatorRow(row_id="1", travel_element="Hotel")) is False
