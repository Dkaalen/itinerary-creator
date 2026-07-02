"""Pure calculator formula calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from calculator.numeric_input import parse_numeric_input
from calculator.row_model import CalculatorRow, CalculatedRow

DEFAULT_CURRENCY_RATES: dict[str, float] = {
    "EUR": 11.3,
    "SEK": 1.02,
    "DKK": 1.5,
    "ISK": 0.075,
    "NOK": 1.0,
    "USD": 10.6,
}


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


def calculate_row(
    row: CalculatorRow,
    currency_rates: Mapping[str, float] | None = None,
) -> CalculatedRow:
    """Apply the Kalk row formulas to one calculator row."""

    rates = currency_rates or DEFAULT_CURRENCY_RATES
    gross_price_per_unit = _number(row.gross_price_per_unit)
    units = _number(row.units)
    supplier_commission = _number(row.supplier_commission)
    gross_price = _override(row.gross_price_override, gross_price_per_unit * units)
    net_price = _override(row.net_price_override, gross_price * (1 - supplier_commission))
    supplier_x_rate = _override(row.supplier_x_rate_override, lookup_currency_rate(row.supplier_currency, rates))
    net_price_nok = _override(row.net_price_nok_override, net_price * supplier_x_rate)
    calculated_sales_price_per_unit = _sales_price_per_unit(row)
    price = _override(row.price_override, calculated_sales_price_per_unit * units)
    sales_x_rate = _override(row.sales_x_rate_override, lookup_currency_rate(row.sales_currency, rates))
    sales_price_nok_total = _override(
        row.sales_price_nok_total_override,
        price * sales_x_rate,
    )
    gp_nok = _override(row.gp_nok_override, sales_price_nok_total - net_price_nok)
    gp_percent = _override(row.gp_percent_override, _safe_ratio(gp_nok, sales_price_nok_total))
    return CalculatedRow(
        source=row,
        gross_price=gross_price,
        net_price=net_price,
        supplier_x_rate=supplier_x_rate,
        net_price_nok=net_price_nok,
        calculated_sales_price_per_unit=calculated_sales_price_per_unit,
        price=price,
        sales_x_rate=sales_x_rate,
        sales_price_nok_total=sales_price_nok_total,
        gp_nok=gp_nok,
        gp_percent=gp_percent,
    )


def calculate_totals(
    rows: tuple[CalculatorRow, ...] | list[CalculatorRow],
    currency_rates: Mapping[str, float] | None = None,
) -> CalculatorTotals:
    """Calculate workbook-style totals across calculator rows."""

    calculated_rows = [calculate_row(row, currency_rates) for row in rows]
    price = sum(row.price for row in calculated_rows)
    sales_price_nok_total = sum(row.sales_price_nok_total for row in calculated_rows)
    gp_nok = sum(row.gp_nok for row in calculated_rows)
    return CalculatorTotals(
        price=price,
        sales_price_nok_total=sales_price_nok_total,
        gp_nok=gp_nok,
        gp_percent=_safe_ratio(gp_nok, sales_price_nok_total),
        vat25=sum(_number(row.vat25) for row in rows),
        vat15=sum(_number(row.vat15) for row in rows),
        vat12=sum(_number(row.vat12) for row in rows),
        vat0_domestic=sum(_number(row.vat0_domestic) for row in rows),
        vat0_international=sum(_number(row.vat0_international) for row in rows),
    )


def lookup_currency_rate(code: str, currency_rates: Mapping[str, float] | None = None) -> float:
    """Return a currency rate using the same zero fallback as the template."""

    rates = currency_rates or DEFAULT_CURRENCY_RATES
    normalized_code = str(code or "").strip().upper()
    return _number(rates.get(normalized_code, 0.0))


def _sales_price_per_unit(row: CalculatorRow) -> float:
    gross_price_per_unit = _number(row.gross_price_per_unit)
    if row.sales_price_per_unit is None:
        return gross_price_per_unit
    sales_price_per_unit = _number(row.sales_price_per_unit)
    if sales_price_per_unit == 0 and gross_price_per_unit > 0:
        return gross_price_per_unit
    return sales_price_per_unit


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _number(value: object) -> float:
    return parse_numeric_input(value)


def _override(value: float | None, calculated: float) -> float:
    if value is None:
        return calculated
    return _number(value)
