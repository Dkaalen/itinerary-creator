"""Canonical calculator formulas with Excel-compatible financial rounding."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from calculator.currency_rates import normalize_currency_rates, normalized_currency_code
from calculator.numeric_input import parse_decimal_input
from calculator.precision import as_float, decimal_value, round_money, round_percent, round_rate
from calculator.row_model import CalculatorRow, CalculatedRow


@dataclass(frozen=True)
class CalculatorTotals:
    """Calculated totals across calculator rows."""

    price: float
    sales_price_nok_total: float
    gp_nok: float
    gp_percent: float
    vat25: float
    vat15: float
    vat12: float
    vat0_domestic: float
    vat0_international: float


@dataclass(frozen=True)
class CalculatorDashboard:
    """Display-only summary metrics; pax never changes row calculations."""

    total_cost_nok: float
    total_sales_nok: float
    profit_nok: float
    margin_percent: float
    number_of_pax: int | None
    cost_per_pax: float | None
    sales_per_pax: float | None


def calculate_row(
    row: CalculatorRow,
    currency_rates: Mapping[str, float] | None = None,
) -> CalculatedRow:
    """Apply the canonical Kalk row formulas to one calculator row."""

    rates = normalize_currency_rates(currency_rates)
    gross_price_per_unit = _decimal(row.gross_price_per_unit)
    units = _decimal(row.units)
    supplier_commission = round_percent(_decimal(row.supplier_commission))

    gross_price = _money_override(row.gross_price_override, gross_price_per_unit * units)
    net_price = _money_override(row.net_price_override, gross_price * (Decimal("1") - supplier_commission))
    supplier_x_rate = _rate_override(
        row.supplier_x_rate_override,
        lookup_currency_rate_decimal(row.supplier_currency, rates),
    )
    net_price_nok = _money_override(row.net_price_nok_override, net_price * supplier_x_rate)
    calculated_sales_price_per_unit = _sales_price_per_unit(row)
    price = _money_override(row.price_override, calculated_sales_price_per_unit * units)
    sales_x_rate = _rate_override(
        row.sales_x_rate_override,
        lookup_currency_rate_decimal(row.sales_currency, rates),
    )
    sales_price_nok_total = _money_override(
        row.sales_price_nok_total_override,
        price * sales_x_rate,
    )
    gp_nok = _money_override(row.gp_nok_override, sales_price_nok_total - net_price_nok)
    gp_percent = _percent_override(row.gp_percent_override, _safe_ratio(gp_nok, sales_price_nok_total))
    return CalculatedRow(
        source=row,
        gross_price=as_float(gross_price),
        net_price=as_float(net_price),
        supplier_x_rate=as_float(supplier_x_rate),
        net_price_nok=as_float(net_price_nok),
        calculated_sales_price_per_unit=as_float(calculated_sales_price_per_unit),
        price=as_float(price),
        sales_x_rate=as_float(sales_x_rate),
        sales_price_nok_total=as_float(sales_price_nok_total),
        gp_nok=as_float(gp_nok),
        gp_percent=as_float(gp_percent),
    )


def calculate_totals(
    rows: tuple[CalculatorRow, ...] | list[CalculatorRow],
    currency_rates: Mapping[str, float] | None = None,
) -> CalculatorTotals:
    """Calculate totals from already rounded canonical row results."""

    rates = normalize_currency_rates(currency_rates)
    calculated_rows = [calculate_row(row, rates) for row in rows]
    price = round_money(sum((_decimal(row.price) for row in calculated_rows), Decimal("0")))
    sales_price_nok_total = round_money(
        sum((_decimal(row.sales_price_nok_total) for row in calculated_rows), Decimal("0"))
    )
    gp_nok = round_money(sum((_decimal(row.gp_nok) for row in calculated_rows), Decimal("0")))
    return CalculatorTotals(
        price=as_float(price),
        sales_price_nok_total=as_float(sales_price_nok_total),
        gp_nok=as_float(gp_nok),
        gp_percent=as_float(_safe_ratio(gp_nok, sales_price_nok_total)),
        vat25=as_float(_sum_money(rows, "vat25")),
        vat15=as_float(_sum_money(rows, "vat15")),
        vat12=as_float(_sum_money(rows, "vat12")),
        vat0_domestic=as_float(_sum_money(rows, "vat0_domestic")),
        vat0_international=as_float(_sum_money(rows, "vat0_international")),
    )


def calculate_dashboard(
    rows: tuple[CalculatorRow, ...] | list[CalculatorRow],
    number_of_pax: int | None,
    currency_rates: Mapping[str, float] | None = None,
) -> CalculatorDashboard:
    """Return display-only dashboard totals and optional per-pax values."""

    rates = normalize_currency_rates(currency_rates)
    calculated_rows = [calculate_row(row, rates) for row in rows]
    total_cost = round_money(sum((_decimal(row.net_price_nok) for row in calculated_rows), Decimal("0")))
    totals = calculate_totals(rows, rates)
    pax = int(number_of_pax) if number_of_pax is not None and int(number_of_pax) > 0 else None
    cost_per_pax = round_money(total_cost / pax) if pax else None
    sales_per_pax = round_money(_decimal(totals.sales_price_nok_total) / pax) if pax else None
    return CalculatorDashboard(
        total_cost_nok=as_float(total_cost),
        total_sales_nok=totals.sales_price_nok_total,
        profit_nok=totals.gp_nok,
        margin_percent=totals.gp_percent,
        number_of_pax=pax,
        cost_per_pax=as_float(cost_per_pax) if cost_per_pax is not None else None,
        sales_per_pax=as_float(sales_per_pax) if sales_per_pax is not None else None,
    )


def lookup_currency_rate(code: str, currency_rates: Mapping[str, float] | None = None) -> float:
    """Return the configured NOK rate, or zero when a code is unknown."""

    return as_float(lookup_currency_rate_decimal(code, currency_rates))


def lookup_currency_rate_decimal(
    code: str,
    currency_rates: Mapping[str, float] | None = None,
) -> Decimal:
    rates = normalize_currency_rates(currency_rates)
    normalized_code = normalized_currency_code(code, default="")
    return round_rate(rates.get(normalized_code, 0.0))


def _sales_price_per_unit(row: CalculatorRow) -> Decimal:
    gross_price_per_unit = _decimal(row.gross_price_per_unit)
    if row.sales_price_per_unit is None:
        return gross_price_per_unit
    sales_price_per_unit = _decimal(row.sales_price_per_unit)
    if sales_price_per_unit == 0 and gross_price_per_unit > 0:
        return gross_price_per_unit
    return sales_price_per_unit


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator


def _decimal(value: object) -> Decimal:
    return parse_decimal_input(value)


def _money_override(value: float | None, calculated: Decimal) -> Decimal:
    return round_money(calculated if value is None else _decimal(value))


def _rate_override(value: float | None, calculated: Decimal) -> Decimal:
    return round_rate(calculated if value is None else _decimal(value))


def _percent_override(value: float | None, calculated: Decimal) -> Decimal:
    return calculated if value is None else round_percent(_decimal(value))


def _sum_money(rows: list[CalculatorRow] | tuple[CalculatorRow, ...], field: str) -> Decimal:
    return round_money(sum((_decimal(getattr(row, field)) for row in rows), Decimal("0")))
