from __future__ import annotations

from app_modules.calculator_grid_values import (
    currency_or_default,
    decimal_to_percent,
    editable_number_value,
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


def test_unfinished_numeric_formulas_are_preserved_for_draft_recovery() -> None:
    assert editable_number_value("=Q7/") == "=Q7/"
    assert editable_number_value("=S7/4") == "=S7/4"


def test_commission_formula_round_trip_preserves_visible_percentage_expression() -> None:
    stored = percent_to_decimal("=Q7")
    assert stored == "=(Q7)/100"
    assert decimal_to_percent(stored) == "=Q7"


def test_invalid_percentage_text_is_preserved_exactly_for_recovery() -> None:
    assert percent_to_decimal("unfinished") == "unfinished"
    assert decimal_to_percent("unfinished") == "unfinished"


def test_calculator_grid_values_normalize_currency_and_blank_rows() -> None:
    assert currency_or_default("") == DEFAULT_CALCULATOR_CURRENCY
    assert currency_or_default("eur") == "EUR"
    assert row_has_no_user_values(CalculatorRow(row_id="1")) is True
    assert row_has_no_user_values(CalculatorRow(row_id="1", travel_element="Hotel")) is False
