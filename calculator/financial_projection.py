"""Immutable canonical financial projection for downstream consumers.

The financial engine calculates.  Consumers such as workbook mutation planners
may map these decisions, but must not re-evaluate pricing, exchange-rate,
commission, VAT, margin, chargeability, or automatic-sales-price rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from calculator.cell_formula_engine import CalculatorCellFormulaEvaluator
from calculator.columns import DATA_START_ROW
from calculator.row_model import CalculatedRow, CalculatorRow

SalesPriceMode = Literal["automatic", "manual"]


@dataclass(frozen=True)
class ProjectedFinancialRow:
    """One canonical calculated row plus downstream mapping decisions."""

    worksheet_row: int
    source: CalculatorRow
    calculated: CalculatedRow
    sales_price_mode: SalesPriceMode
    has_positive_supplier_cost: bool


@dataclass(frozen=True)
class CalculatorFinancialProjection:
    """Immutable financial projection for a complete Calculator workspace."""

    rows: tuple[ProjectedFinancialRow, ...]


def project_calculator_financials(
    rows: Sequence[CalculatorRow],
    currency_rates: Mapping[str, float] | None = None,
) -> CalculatorFinancialProjection:
    """Calculate all financial decisions exactly once for downstream mapping."""

    source_rows = tuple(rows)
    evaluator = CalculatorCellFormulaEvaluator(source_rows, currency_rates)
    calculated_rows = evaluator.calculated_rows()
    projected: list[ProjectedFinancialRow] = []
    for index, (source, calculated) in enumerate(zip(source_rows, calculated_rows)):
        worksheet_row = DATA_START_ROW + index
        projected.append(
            ProjectedFinancialRow(
                worksheet_row=worksheet_row,
                source=source,
                calculated=calculated,
                sales_price_mode=_sales_price_mode(source, worksheet_row, evaluator),
                has_positive_supplier_cost=calculated.net_price_nok > 0,
            )
        )
    return CalculatorFinancialProjection(rows=tuple(projected))


def _sales_price_mode(
    row: CalculatorRow,
    worksheet_row: int,
    evaluator: CalculatorCellFormulaEvaluator,
) -> SalesPriceMode:
    value = row.sales_price_per_unit
    if value in (None, ""):
        return "automatic"
    parsed = evaluator.evaluate_expression(value, current_cell=f"Y{worksheet_row}")
    gross = evaluator.evaluate_cell(f"Q{worksheet_row}")
    if parsed == 0 and gross > 0:
        return "automatic"
    return "manual"


__all__ = [
    "CalculatorFinancialProjection",
    "ProjectedFinancialRow",
    "SalesPriceMode",
    "project_calculator_financials",
]
