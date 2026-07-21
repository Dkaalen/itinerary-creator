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
    assert calculated.supplier_x_rate == 11
    assert isclose(calculated.net_price_nok, 1980)
    assert calculated.calculated_sales_price_per_unit == 1100
    assert calculated.price == 2200
    assert calculated.sales_x_rate == 1
    assert calculated.sales_price_nok_total == 2200
    assert isclose(calculated.gp_nok, 220)
    assert isclose(calculated.gp_percent, 0.1)


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
    assert calculated.sales_x_rate == 11
    assert isclose(calculated.sales_price_nok_total, 4950)
    assert isclose(calculated.gp_nok, 4710)
    assert isclose(calculated.gp_percent, 4710 / 4950)


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
    assert isclose(calculated.sales_price_nok_total, 2530)
    assert isclose(calculated.net_price_nok, 1619.2)
    assert isclose(calculated.gp_nok, 910.8)
    assert isclose(calculated.gp_percent, 910.8 / 2530)


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


def test_calculator_rounds_money_like_excel_half_away_from_zero() -> None:
    positive = calculate_row(
        CalculatorRow(gross_price_per_unit=1.005, units=1, supplier_currency="NOK", sales_currency="NOK")
    )
    negative = calculate_row(
        CalculatorRow(gross_price_per_unit=-1.005, units=1, supplier_currency="NOK", sales_currency="NOK")
    )

    assert positive.gross_price == 1.01
    assert positive.sales_price_nok_total == 1.01
    assert negative.gross_price == -1.01
    assert negative.sales_price_nok_total == -1.01


def test_zero_units_remain_zero_in_canonical_engine() -> None:
    calculated = calculate_row(
        CalculatorRow(gross_price_per_unit=100, units=0, supplier_currency="NOK", sales_currency="NOK")
    )

    assert calculated.gross_price == 0
    assert calculated.sales_price_nok_total == 0


def test_dashboard_pax_values_are_display_only() -> None:
    from calculator.calculations import calculate_dashboard

    rows = [
        CalculatorRow(
            gross_price_per_unit=100,
            units=2,
            supplier_currency="NOK",
            sales_price_per_unit=150,
            sales_currency="NOK",
        )
    ]

    dashboard = calculate_dashboard(rows, 4)
    without_pax = calculate_dashboard(rows, None)

    assert dashboard.total_cost_nok == 200
    assert dashboard.total_sales_nok == 300
    assert dashboard.cost_per_pax == 50
    assert dashboard.sales_per_pax == 75
    assert without_pax.cost_per_pax is None
    assert without_pax.sales_per_pax is None


def test_calculator_rounds_spreadsheet_expressions_with_decimal_precision() -> None:
    calculated = calculate_row(
        CalculatorRow(
            gross_price_per_unit="=404.775*12.2",
            units=1,
            supplier_currency="NOK",
            sales_currency="NOK",
        )
    )

    assert calculated.gross_price == 4938.26


def test_default_sales_price_converts_supplier_currency_into_sales_currency() -> None:
    calculated = calculate_row(
        CalculatorRow(
            gross_price_per_unit=1200,
            units=2,
            supplier_currency="NOK",
            sales_currency="EUR",
        ),
        {"NOK": 1, "EUR": 12},
    )

    assert calculated.calculated_sales_price_per_unit == 100
    assert calculated.price == 200
    assert calculated.sales_price_nok_total == 2400
    assert calculated.gp_nok == 0


def test_dashboard_ignores_fractional_or_invalid_pax_without_crashing() -> None:
    from calculator.calculations import calculate_dashboard

    rows = [CalculatorRow(gross_price_per_unit=100, units=1, supplier_currency="NOK", sales_currency="NOK")]

    assert calculate_dashboard(rows, "2.5").number_of_pax is None
    assert calculate_dashboard(rows, "unfinished").number_of_pax is None
    assert calculate_dashboard(rows, "2.0").number_of_pax == 2
