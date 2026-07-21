"""Canonical workbook export decisions shared by every XLSX renderer.

The plan owns calculator-to-cell mappings, value kinds, formula restoration,
currency rows, totals, payments, and blank-row behaviour. Renderers only apply
this immutable plan to the reference workbook.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Literal, Mapping

from calculator.calculator_state import CalculatorState
from calculator.cell_formula_engine import CalculatorCellFormulaEvaluator
from calculator.columns import DATA_END_ROW, DATA_START_ROW, TOTALS_ROW
from calculator.currency_rates import normalize_currency_rates
from calculator.formula_map import (
    LEGACY_PAYMENT_CELLS_TO_CLEAR,
    PAYMENT_FORMULAS,
    TOTAL_FORMULAS,
    expected_row_formulas,
)
from calculator.row_model import FORMULA_OVERRIDE_FIELD_BY_KEY, CalculatorRow

CellValueKind = Literal["blank", "boolean", "formula", "number", "text"]

CURRENCY_START_ROW = 2
CURRENCY_ROW_COUNT = 12
QUOTE_CELL = "Z103"
QUOTE_FORMULA = f"=Z{TOTALS_ROW}"

ROW_VALUE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("B", "row_id"),
    ("C", "day"),
    ("D", "type"),
    ("E", "from_date"),
    ("F", "to_date"),
    ("G", "from_time"),
    ("H", "to_time"),
    ("I", "supplier"),
    ("J", "travel_element"),
    ("K", "manual_booking"),
    ("L", "status"),
    ("M", "comments"),
    ("N", "non_refundable"),
    ("O", "refundable"),
    ("P", "url"),
    ("Q", "gross_price_per_unit"),
    ("R", "units"),
    ("T", "supplier_commission"),
    ("V", "supplier_currency"),
    ("AA", "sales_currency"),
    ("AF", "vat25"),
    ("AG", "vat15"),
    ("AH", "vat12"),
    ("AI", "vat0_domestic"),
    ("AJ", "vat0_international"),
)
FORMULA_FIELD_BY_COLUMN: tuple[tuple[str, str], ...] = (
    ("S", "gross_price"),
    ("U", "net_price"),
    ("W", "supplier_x_rate"),
    ("X", "net_price_nok"),
    ("Z", "price"),
    ("AB", "sales_x_rate"),
    ("AC", "sales_price_nok_total"),
    ("AD", "gp_nok"),
    ("AE", "gp_percent"),
)
BOOLEAN_FIELDS = frozenset({"manual_booking", "non_refundable", "refundable"})
CURRENCY_FIELDS = frozenset({"supplier_currency", "sales_currency"})
NUMERIC_INPUT_FIELDS = frozenset(
    {
        "gross_price_per_unit",
        "units",
        "supplier_commission",
        "vat25",
        "vat15",
        "vat12",
        "vat0_domestic",
        "vat0_international",
    }
)


@dataclass(frozen=True)
class ExportCell:
    """One explicit cell mutation in a workbook export."""

    reference: str
    value: object
    kind: CellValueKind


@dataclass(frozen=True)
class WorkbookExportPlan:
    """Complete renderer-independent workbook mutation plan."""

    currency_cells: tuple[ExportCell, ...]
    calculator_cells: tuple[ExportCell, ...]
    calculation_properties: tuple[tuple[str, object], ...]
    fingerprint: str

    def currency_cell_map(self) -> dict[str, ExportCell]:
        return {cell.reference: cell for cell in self.currency_cells}

    def calculator_cell_map(self) -> dict[str, ExportCell]:
        return {cell.reference: cell for cell in self.calculator_cells}


CALCULATION_PROPERTIES: tuple[tuple[str, object], ...] = (
    ("calcMode", "auto"),
    ("fullCalcOnLoad", True),
    ("forceFullCalc", True),
)


def ensure_workbook_export_capacity(state: CalculatorState) -> None:
    """Raise when calculator rows exceed the retained template capacity."""

    max_rows = DATA_END_ROW - DATA_START_ROW + 1
    if len(state.rows) > max_rows:
        raise ValueError(f"Calculator export supports at most {max_rows} rows.")


def build_workbook_export_plan(
    state: CalculatorState,
    currency_rates: Mapping[str, float] | None = None,
) -> WorkbookExportPlan:
    """Build the one authoritative plan consumed by both XLSX renderers."""

    ensure_workbook_export_capacity(state)
    rows = tuple(state.rows)

    rates = normalize_currency_rates(currency_rates)
    currency_cells = _currency_cells(rates, rows)
    calculator_cells = _calculator_cells(rows, rates)
    properties = CALCULATION_PROPERTIES
    fingerprint = _plan_fingerprint(currency_cells, calculator_cells, properties)
    return WorkbookExportPlan(
        currency_cells=currency_cells,
        calculator_cells=calculator_cells,
        calculation_properties=properties,
        fingerprint=fingerprint,
    )


def _currency_cells(
    rates: Mapping[str, float],
    rows: tuple[CalculatorRow, ...],
) -> tuple[ExportCell, ...]:
    cells: list[ExportCell] = []
    items = _selected_currency_items(rates, rows)
    for offset in range(CURRENCY_ROW_COUNT):
        row_number = CURRENCY_START_ROW + offset
        if offset < len(items):
            code, rate = items[offset]
            cells.append(ExportCell(f"B{row_number}", str(code).upper(), "text"))
            cells.append(ExportCell(f"C{row_number}", rate, "number"))
        else:
            cells.append(ExportCell(f"B{row_number}", None, "blank"))
            cells.append(ExportCell(f"C{row_number}", None, "blank"))
    return tuple(cells)


def _selected_currency_items(
    rates: Mapping[str, float],
    rows: tuple[CalculatorRow, ...],
) -> tuple[tuple[str, float], ...]:
    required = _required_lookup_currencies(rows)
    missing = [code for code in required if code not in rates]
    if missing:
        raise ValueError(f"Workbook export has no exchange rate for {', '.join(missing)}.")
    if len(required) > CURRENCY_ROW_COUNT:
        raise ValueError(
            f"Workbook export supports at most {CURRENCY_ROW_COUNT} currencies without manual rate overrides."
        )

    selected = list(rates.items())[:CURRENCY_ROW_COUNT]
    selected_codes = {code for code, _ in selected}
    required_set = set(required)
    for code in required:
        if code in selected_codes:
            continue
        replacement = next(
            (
                index
                for index in range(len(selected) - 1, -1, -1)
                if selected[index][0] not in required_set
            ),
            None,
        )
        if replacement is None:
            raise ValueError(
                f"Workbook export cannot fit required currency {code} in the {CURRENCY_ROW_COUNT}-row lookup table."
            )
        selected_codes.discard(selected[replacement][0])
        selected[replacement] = (code, rates[code])
        selected_codes.add(code)
    return tuple(selected)


def _required_lookup_currencies(rows: tuple[CalculatorRow, ...]) -> tuple[str, ...]:
    required: list[str] = []
    for row in rows:
        for field_name, override_field in (
            ("supplier_currency", "supplier_x_rate_override"),
            ("sales_currency", "sales_x_rate_override"),
        ):
            if getattr(row, override_field) is not None:
                continue
            code = str(getattr(row, field_name) or "EUR").strip().upper() or "EUR"
            if code not in required:
                required.append(code)
    return tuple(required)


def _calculator_cells(
    rows: tuple[CalculatorRow, ...],
    rates: Mapping[str, float],
) -> tuple[ExportCell, ...]:
    evaluator = CalculatorCellFormulaEvaluator(rows, rates)
    cells: list[ExportCell] = []
    for row_offset, row_number in enumerate(range(DATA_START_ROW, DATA_END_ROW + 1)):
        row = rows[row_offset] if row_offset < len(rows) else None
        cells.extend(_data_row_cells(row_number, row, evaluator))

    for reference, formula in {**TOTAL_FORMULAS, **PAYMENT_FORMULAS, QUOTE_CELL: QUOTE_FORMULA}.items():
        cells.append(ExportCell(reference, formula, "formula"))
    for reference in LEGACY_PAYMENT_CELLS_TO_CLEAR:
        cells.append(ExportCell(reference, None, "blank"))
    return tuple(cells)


def _data_row_cells(
    row_number: int,
    row: CalculatorRow | None,
    evaluator: CalculatorCellFormulaEvaluator,
) -> tuple[ExportCell, ...]:
    cells: list[ExportCell] = []
    for column, field_name in ROW_VALUE_COLUMNS:
        value = None if row is None else _row_cell_value(row, field_name)
        cells.append(_planned_cell(f"{column}{row_number}", value, _row_value_kind(field_name, value)))

    sales_value = (
        expected_row_formulas(row_number)["Y"]
        if row is None
        else _sales_price_cell_value(row, row_number, evaluator)
    )
    cells.append(_planned_cell(f"Y{row_number}", sales_value, _numeric_or_formula_kind(sales_value)))

    formula_fields = dict(FORMULA_FIELD_BY_COLUMN)
    for column, formula in expected_row_formulas(row_number).items():
        if column == "Y":
            continue
        value: object = formula
        if row is not None:
            field_name = formula_fields.get(column, "")
            override_field = FORMULA_OVERRIDE_FIELD_BY_KEY.get(field_name, "")
            override_value = getattr(row, override_field, None) if override_field else None
            if override_value is not None:
                value = override_value
        cells.append(_planned_cell(f"{column}{row_number}", value, _numeric_or_formula_kind(value)))
    return tuple(cells)


def _row_cell_value(row: CalculatorRow, field_name: str) -> object:
    value = getattr(row, field_name)
    if field_name == "row_id" and not value:
        return None
    if field_name in CURRENCY_FIELDS:
        return str(value or "EUR").upper()
    return value


def _row_value_kind(field_name: str, value: object) -> CellValueKind:
    if value in (None, ""):
        return "blank"
    if field_name in BOOLEAN_FIELDS:
        return "boolean"
    if field_name in NUMERIC_INPUT_FIELDS:
        return _numeric_or_formula_kind(value)
    return "text"


def _sales_price_cell_value(
    row: CalculatorRow,
    row_number: int,
    evaluator: CalculatorCellFormulaEvaluator,
) -> object:
    value = row.sales_price_per_unit
    automatic_formula = expected_row_formulas(row_number)["Y"]
    if value in (None, ""):
        return automatic_formula
    parsed = evaluator.evaluate_expression(value, current_cell=f"Y{row_number}")
    gross = evaluator.evaluate_cell(f"Q{row_number}")
    if parsed == 0 and gross > 0:
        return automatic_formula
    return value


def _numeric_or_formula_kind(value: object) -> CellValueKind:
    if value in (None, ""):
        return "blank"
    if isinstance(value, str) and value.strip().startswith("="):
        return "formula"
    return "number"


def _planned_cell(reference: str, value: object, kind: CellValueKind) -> ExportCell:
    return ExportCell(reference, value, kind)


def _plan_fingerprint(
    currency_cells: tuple[ExportCell, ...],
    calculator_cells: tuple[ExportCell, ...],
    properties: tuple[tuple[str, object], ...],
) -> str:
    digest = hashlib.sha256()
    for cell in (*currency_cells, *calculator_cells):
        digest.update(cell.reference.encode("utf-8"))
        digest.update(b"\0")
        digest.update(cell.kind.encode("ascii"))
        digest.update(b"\0")
        digest.update(repr(cell.value).encode("utf-8"))
        digest.update(b"\0")
    for name, value in properties:
        digest.update(name.encode("ascii"))
        digest.update(b"=")
        digest.update(repr(value).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
