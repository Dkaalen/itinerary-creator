from __future__ import annotations

import pytest
from calculator.row_model import (
    ADVANCED_FIELD_KEYS,
    BASIC_FIELD_KEYS,
    FORMULA_FIELD_KEYS,
    VAT_FIELD_KEYS,
    CalculatorRow,
)


def test_calculator_row_defaults_are_safe_for_new_blank_lines() -> None:
    row = CalculatorRow()

    assert row.row_id == ""
    assert row.supplier_currency == "EUR"
    assert row.sales_currency == "EUR"
    assert row.sales_price_per_unit is None
    assert row.gross_price_per_unit == 0
    assert row.units == 0
    assert row.gross_price_override is None
    assert row.gp_percent_override is None


def test_calculator_row_field_groups_are_locked() -> None:
    assert BASIC_FIELD_KEYS == (
        "row_id",
        "day",
        "type",
        "from_date",
        "to_date",
        "travel_element",
        "url",
        "gross_price_per_unit",
        "units",
        "supplier_commission",
        "supplier_currency",
        "sales_price_per_unit",
        "sales_currency",
    )
    assert ADVANCED_FIELD_KEYS == (
        "from_time",
        "to_time",
        "supplier",
        "manual_booking",
        "status",
        "comments",
        "non_refundable",
        "refundable",
        "vat25",
        "vat15",
        "vat12",
        "vat0_domestic",
        "vat0_international",
    )
    assert VAT_FIELD_KEYS == (
        "vat25",
        "vat15",
        "vat12",
        "vat0_domestic",
        "vat0_international",
    )
    assert FORMULA_FIELD_KEYS == (
        "gross_price",
        "net_price",
        "supplier_x_rate",
        "net_price_nok",
        "price",
        "sales_x_rate",
        "sales_price_nok_total",
        "gp_nok",
        "gp_percent",
    )


def test_calculator_row_with_changes_returns_updated_copy() -> None:
    row = CalculatorRow(travel_element="Old")

    updated = row.with_changes(travel_element="New", units=2)

    assert row.travel_element == "Old"
    assert updated.travel_element == "New"
    assert updated.units == 2


def test_sales_price_per_unit_zero_defaults_to_gross_price_for_calculation() -> None:
    from calculator.calculations import calculate_row
    from calculator.row_model import CalculatorRow

    calculated = calculate_row(
        CalculatorRow(
            row_id="1",
            travel_element="Activity",
            gross_price_per_unit=252,
            units=1,
            supplier_commission=0.2,
            supplier_currency="EUR",
            sales_price_per_unit=0,
            sales_currency="EUR",
        )
    )

    assert calculated.calculated_sales_price_per_unit == 252
    assert calculated.price == 252
    assert calculated.sales_price_nok_total == pytest.approx(2772.0)
    assert calculated.gp_nok == pytest.approx(554.4)
