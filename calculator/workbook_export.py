"""Export calculator state into the calculation workbook template."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

from openpyxl.workbook.workbook import Workbook

from calculator.calculator_state import CalculatorState
from calculator.columns import DATA_END_ROW, DATA_START_ROW, KALK_SHEET_NAME, TOTALS_ROW
from calculator.filename_sanitizer import calculation_workbook_filename
from calculator.formula_map import expected_row_formulas
from calculator.row_model import CalculatorRow
from calculator.workbook_template import load_calculation_template

_MAX_DATA_ROWS = DATA_END_ROW - DATA_START_ROW + 1
_QUOTE_CELL = "Z103"
_COLLAPSED_GROUP_MARKERS = ("J", "P", "AK")
_ROW_VALUE_COLUMNS = {
    "B": "row_id",
    "C": "day",
    "D": "type",
    "E": "from_date",
    "F": "to_date",
    "G": "from_time",
    "H": "to_time",
    "I": "supplier",
    "J": "travel_element",
    "K": "manual_booking",
    "L": "status",
    "M": "comments",
    "N": "non_refundable",
    "O": "refundable",
    "P": "url",
    "Q": "gross_price_per_unit",
    "R": "units",
    "T": "supplier_commission",
    "V": "supplier_currency",
    "AA": "sales_currency",
    "AF": "vat25",
    "AG": "vat15",
    "AH": "vat12",
    "AI": "vat0_domestic",
    "AJ": "vat0_international",
}


@dataclass(frozen=True)
class WorkbookExport:
    """Generated workbook download payload."""

    filename: str
    content: bytes


def export_calculation_workbook(
    state: CalculatorState,
    template_path: str | Path | None = None,
) -> WorkbookExport:
    """Return an XLSX payload for the supplied calculator state."""

    workbook = build_calculation_workbook(state, template_path)
    buffer = BytesIO()
    workbook.save(buffer)
    return WorkbookExport(
        filename=calculation_workbook_filename(state.itinerary_name),
        content=buffer.getvalue(),
    )


def save_calculation_workbook(
    state: CalculatorState,
    output_dir: str | Path,
    template_path: str | Path | None = None,
) -> Path:
    """Write the exported calculation workbook to a directory."""

    export = export_calculation_workbook(state, template_path)
    output_path = Path(output_dir) / export.filename
    output_path.write_bytes(export.content)
    return output_path


def build_calculation_workbook(
    state: CalculatorState,
    template_path: str | Path | None = None,
) -> Workbook:
    """Fill a fresh template workbook with calculator rows."""

    rows = tuple(state.rows)
    if len(rows) > _MAX_DATA_ROWS:
        raise ValueError(f"Calculator export supports at most {_MAX_DATA_ROWS} rows.")

    workbook = load_calculation_template(template_path)
    sheet = workbook[KALK_SHEET_NAME]
    for row_number, row in zip(_data_row_numbers(), rows):
        _write_row(sheet, row_number, row)
    sheet[_QUOTE_CELL] = f"=Z{TOTALS_ROW}"
    _clean_export_view(sheet)
    return workbook


def _data_row_numbers() -> Iterable[int]:
    return range(DATA_START_ROW, DATA_END_ROW + 1)


def _write_row(sheet: object, row_number: int, row: CalculatorRow) -> None:
    for column, field_name in _ROW_VALUE_COLUMNS.items():
        sheet[f"{column}{row_number}"] = _cell_value(row, field_name)
    _write_sales_price_cell(sheet, row_number, row)
    _restore_formula_cells(sheet, row_number)


def _write_sales_price_cell(sheet: object, row_number: int, row: CalculatorRow) -> None:
    cell = sheet[f"Y{row_number}"]
    value = row.sales_price_per_unit
    if value is None:
        cell.value = f"=Q{row_number}"
        return
    cell.value = value


def _restore_formula_cells(sheet: object, row_number: int) -> None:
    formulas = expected_row_formulas(row_number)
    for column, formula in formulas.items():
        if column == "Y":
            continue
        sheet[f"{column}{row_number}"] = formula


def _cell_value(row: CalculatorRow, field_name: str) -> object:
    value = getattr(row, field_name)
    if field_name == "row_id" and not value:
        return None
    if field_name in {"supplier_currency", "sales_currency"}:
        return str(value or "EUR").upper()
    return value


def _clean_export_view(sheet: object) -> None:
    """Remove collapsed-group markers that render as ugly vertical artifacts."""

    for column in _COLLAPSED_GROUP_MARKERS:
        if column in sheet.column_dimensions:
            sheet.column_dimensions[column].collapsed = False
    sheet.sheet_view.showOutlineSymbols = False
