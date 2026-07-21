"""Canonical calculator formulas with Excel-compatible financial rounding."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from typing import Mapping

from calculator.cell_formula_engine import CalculatorCellFormulaEvaluator
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
    """Apply canonical formulas to one row.

    Cross-row A1 formulas require :func:`calculate_rows`, which evaluates the
    complete dependency graph.
    """

    return calculate_rows((row,), currency_rates)[0]


def calculate_rows(
    rows: tuple[CalculatorRow, ...] | list[CalculatorRow],
    currency_rates: Mapping[str, float] | None = None,
) -> tuple[CalculatedRow, ...]:
    """Calculate all rows with A1 dependency and circular-reference handling."""

    evaluator = CalculatorCellFormulaEvaluator(rows, currency_rates)
    return evaluator.calculated_rows()


def calculate_totals(
    rows: tuple[CalculatorRow, ...] | list[CalculatorRow],
    currency_rates: Mapping[str, float] | None = None,
) -> CalculatorTotals:
    """Calculate totals from already rounded canonical row results."""

    evaluator = CalculatorCellFormulaEvaluator(rows, currency_rates)
    calculated_rows = evaluator.calculated_rows()
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
        vat25=as_float(_sum_formula_cells(evaluator, "AF", len(rows))),
        vat15=as_float(_sum_formula_cells(evaluator, "AG", len(rows))),
        vat12=as_float(_sum_formula_cells(evaluator, "AH", len(rows))),
        vat0_domestic=as_float(_sum_formula_cells(evaluator, "AI", len(rows))),
        vat0_international=as_float(_sum_formula_cells(evaluator, "AJ", len(rows))),
    )


def calculate_dashboard(
    rows: tuple[CalculatorRow, ...] | list[CalculatorRow],
    number_of_pax: int | str | None,
    currency_rates: Mapping[str, float] | None = None,
) -> CalculatorDashboard:
    """Return display-only dashboard totals and optional per-pax values."""

    evaluator = CalculatorCellFormulaEvaluator(rows, currency_rates)
    calculated_rows = evaluator.calculated_rows()
    total_cost = round_money(sum((_decimal(row.net_price_nok) for row in calculated_rows), Decimal("0")))
    total_sales = round_money(
        sum((_decimal(row.sales_price_nok_total) for row in calculated_rows), Decimal("0"))
    )
    profit = round_money(sum((_decimal(row.gp_nok) for row in calculated_rows), Decimal("0")))
    margin = _safe_ratio(profit, total_sales)
    pax = _positive_whole_pax_or_none(number_of_pax)
    cost_per_pax = round_money(total_cost / pax) if pax else None
    sales_per_pax = round_money(total_sales / pax) if pax else None
    return CalculatorDashboard(
        total_cost_nok=as_float(total_cost),
        total_sales_nok=as_float(total_sales),
        profit_nok=as_float(profit),
        margin_percent=as_float(margin),
        number_of_pax=pax,
        cost_per_pax=as_float(cost_per_pax) if cost_per_pax is not None else None,
        sales_per_pax=as_float(sales_per_pax) if sales_per_pax is not None else None,
    )


def _positive_whole_pax_or_none(value: object) -> int | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number <= 0 or not number.is_integer():
        return None
    return int(number)


def _sum_formula_cells(evaluator: CalculatorCellFormulaEvaluator, column: str, count: int) -> Decimal:
    return round_money(
        sum((evaluator.evaluate_cell(f"{column}{7 + index}") for index in range(count)), Decimal("0"))
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
