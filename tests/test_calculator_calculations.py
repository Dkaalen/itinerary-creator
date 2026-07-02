from __future__ import annotations

from math import isclose

from calculator.calculations import calculate_row, calculate_totals, lookup_currency_rate
from calculator.row_model import CalculatorRow


def test_calculate_row_matches_core_kalk_formulas_with_default_sales_price() -> None:
    row = CalculatorRow(
        row_id="1",
        gross_price_per_unit=100,
        units=2,
        supplier_commission=0.10,
        supplier_currency="EUR",
        sales_currency="NOK",
    )

    calculated = calculate_row(row)

    assert calculated.gross_price == 200
    assert calculated.net_price == 180
    assert calculated.supplier_x_rate == 11.3
    assert isclose(calculated.net_price_nok, 2034)
    assert calculated.calculated_sales_price_per_unit == 100
    assert calculated.price == 200
    assert calculated.sales_x_rate == 1
    assert calculated.sales_price_nok_total == 200
    assert isclose(calculated.gp_nok, -1834)
    assert isclose(calculated.gp_percent, -9.17)


def test_calculate_row_uses_sales_price_override_and_sales_currency() -> None:
    row = CalculatorRow(
        row_id="1",
        gross_price_per_unit=100,
        units=3,
        supplier_commission=0.20,
        supplier_currency="NOK",
        sales_price_per_unit=150,
        sales_currency="EUR",
    )

    calculated = calculate_row(row)

    assert calculated.gross_price == 300
    assert calculated.net_price == 240
    assert calculated.net_price_nok == 240
    assert calculated.calculated_sales_price_per_unit == 150
    assert calculated.price == 450
    assert calculated.sales_x_rate == 11.3
    assert isclose(calculated.sales_price_nok_total, 5085)
    assert isclose(calculated.gp_nok, 4845)
    assert isclose(calculated.gp_percent, 4845 / 5085)


def test_price_override_recalculates_sales_nok_and_gp_from_actual_price() -> None:
    row = CalculatorRow(
        row_id="1",
        gross_price_per_unit=184,
        units=1,
        supplier_commission=0.20,
        supplier_currency="EUR",
        price_override=230,
        sales_currency="EUR",
    )

    calculated = calculate_row(row)

    assert isclose(calculated.net_price, 147.2)
    assert calculated.price == 230
    assert isclose(calculated.sales_price_nok_total, 2599)
    assert isclose(calculated.net_price_nok, 1663.36)
    assert isclose(calculated.gp_nok, 935.64)
    assert isclose(calculated.gp_percent, 935.64 / 2599)


def test_unknown_currency_rate_falls_back_to_zero_like_template() -> None:
    row = CalculatorRow(
        gross_price_per_unit=100,
        units=1,
        supplier_currency="BAD",
        sales_currency="BAD",
    )

    calculated = calculate_row(row)

    assert lookup_currency_rate("BAD") == 0
    assert calculated.supplier_x_rate == 0
    assert calculated.sales_x_rate == 0
    assert calculated.net_price_nok == 0
    assert calculated.sales_price_nok_total == 0
    assert calculated.gp_percent == 0


def test_calculate_totals_sums_money_gp_and_vat_fields() -> None:
    rows = [
        CalculatorRow(
            gross_price_per_unit=100,
            units=2,
            supplier_commission=0,
            supplier_currency="NOK",
            sales_price_per_unit=150,
            sales_currency="NOK",
            vat25=10,
            vat15=1,
        ),
        CalculatorRow(
            gross_price_per_unit=50,
            units=4,
            supplier_commission=0.5,
            supplier_currency="NOK",
            sales_price_per_unit=100,
            sales_currency="NOK",
            vat25=20,
            vat12=2,
            vat0_domestic=3,
            vat0_international=4,
        ),
    ]

    totals = calculate_totals(rows)

    assert totals.price == 700
    assert totals.sales_price_nok_total == 700
    assert totals.gp_nok == 400
    assert isclose(totals.gp_percent, 400 / 700)
    assert totals.vat25 == 30
    assert totals.vat15 == 1
    assert totals.vat12 == 2
    assert totals.vat0_domestic == 3
    assert totals.vat0_international == 4
