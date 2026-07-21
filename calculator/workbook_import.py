"""Import calculator data from the reference-compatible Excel workbook."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import re
from typing import Mapping
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from calculator.calculator_state import CalculatorState
from calculator.columns import DATA_END_ROW, DATA_START_ROW
from calculator.formula_map import expected_row_formulas
from calculator.financial_rules import unwrap_canonical_export_formula
from calculator.row_model import FORMULA_OVERRIDE_FIELD_BY_KEY, CalculatorRow
from calculator.workbook_export_plan import FORMULA_FIELD_BY_COLUMN, ROW_VALUE_COLUMNS

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS = {"x": _MAIN_NS}
_CURR_SHEET = "xl/worksheets/sheet1.xml"
_KALK_SHEET = "xl/worksheets/sheet2.xml"
_SHARED_STRINGS = "xl/sharedStrings.xml"

_ROW_VALUE_COLUMNS = dict(ROW_VALUE_COLUMNS)
_FORMULA_FIELD_BY_COLUMN = dict(FORMULA_FIELD_BY_COLUMN)
_TEXT_FIELDS = {
    "row_id",
    "day",
    "type",
    "from_date",
    "to_date",
    "from_time",
    "to_time",
    "supplier",
    "travel_element",
    "status",
    "comments",
    "url",
    "supplier_currency",
    "sales_currency",
}
_BOOLEAN_FIELDS = {"manual_booking", "non_refundable", "refundable"}
_DATE_FIELDS = {"from_date", "to_date"}


@dataclass(frozen=True)
class WorkbookImportResult:
    """Imported calculator state, workbook rates, and non-blocking warnings."""

    state: CalculatorState
    currency_rates: dict[str, float]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _CellData:
    value: object = None
    formula: str | None = None


def import_calculation_workbook(
    content: bytes | bytearray | memoryview,
    *,
    filename: str = "",
) -> WorkbookImportResult:
    """Read calculator rows and currency rates from a compatible XLSX payload."""

    try:
        with ZipFile(BytesIO(bytes(content)), "r") as workbook:
            required = {_CURR_SHEET, _KALK_SHEET}
            missing = required.difference(workbook.namelist())
            if missing:
                raise ValueError("Workbook does not contain the expected Curr and Kalk worksheets.")
            shared_strings = _read_shared_strings(workbook)
            currency_cells = _read_sheet_cells(workbook.read(_CURR_SHEET), shared_strings)
            calculator_cells = _read_sheet_cells(workbook.read(_KALK_SHEET), shared_strings)
    except BadZipFile as error:
        raise ValueError("The selected file is not a valid Excel workbook.") from error

    currency_rates = _read_currency_rates(currency_cells)
    rows, warnings = _read_calculator_rows(calculator_cells)
    itinerary_name = _itinerary_name_from_filename(filename)
    return WorkbookImportResult(
        state=CalculatorState(itinerary_name=itinerary_name, rows=rows),
        currency_rates=currency_rates,
        warnings=warnings,
    )


def _read_shared_strings(workbook: ZipFile) -> tuple[str, ...]:
    if _SHARED_STRINGS not in workbook.namelist():
        return ()
    root = ET.fromstring(workbook.read(_SHARED_STRINGS))
    strings: list[str] = []
    for item in root.findall("x:si", _NS):
        strings.append("".join(node.text or "" for node in item.findall(".//x:t", _NS)))
    return tuple(strings)


def _read_sheet_cells(xml_bytes: bytes, shared_strings: tuple[str, ...]) -> dict[str, _CellData]:
    root = ET.fromstring(xml_bytes)
    cells: dict[str, _CellData] = {}
    for cell in root.findall(".//x:c", _NS):
        reference = str(cell.attrib.get("r") or "").upper()
        if not reference:
            continue
        formula_node = cell.find("x:f", _NS)
        formula_text = (formula_node.text or "").strip() if formula_node is not None else ""
        formula = f"={formula_text}" if formula_text else None
        cell_type = cell.attrib.get("t")
        value_node = cell.find("x:v", _NS)
        raw_value = value_node.text if value_node is not None else None
        value: object = None
        if cell_type == "inlineStr":
            value = "".join(node.text or "" for node in cell.findall(".//x:t", _NS))
        elif cell_type == "s" and raw_value is not None:
            try:
                value = shared_strings[int(raw_value)]
            except (IndexError, ValueError):
                value = ""
        elif cell_type == "b":
            value = raw_value == "1"
        elif raw_value not in (None, ""):
            value = _numeric_value(raw_value)
        cells[reference] = _CellData(value=value, formula=formula)
    return cells


def _numeric_value(value: str) -> int | float | str:
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return int(number)
    return number


def _read_currency_rates(cells: Mapping[str, _CellData]) -> dict[str, float]:
    rates: dict[str, float] = {}
    for row_number in range(2, 14):
        code = str(cells.get(f"B{row_number}", _CellData()).value or "").strip().upper()
        value = cells.get(f"C{row_number}", _CellData()).value
        if not code or not isinstance(value, (int, float)):
            continue
        rates[code] = float(value)
    return rates


def _read_calculator_rows(cells: Mapping[str, _CellData]) -> tuple[tuple[CalculatorRow, ...], tuple[str, ...]]:
    imported: list[CalculatorRow] = []
    meaningful_indexes: list[int] = []
    warnings: list[str] = []
    for index, row_number in enumerate(range(DATA_START_ROW, DATA_END_ROW + 1)):
        values: dict[str, object] = {}
        for column, field_name in _ROW_VALUE_COLUMNS.items():
            values[field_name] = _field_value(field_name, cells.get(f"{column}{row_number}", _CellData()))

        values["sales_price_per_unit"] = _sales_price_value(cells.get(f"Y{row_number}", _CellData()), row_number)
        canonical = expected_row_formulas(row_number)
        for column, formula_field in _FORMULA_FIELD_BY_COLUMN.items():
            override_field = FORMULA_OVERRIDE_FIELD_BY_KEY[formula_field]
            cell = cells.get(f"{column}{row_number}", _CellData())
            values[override_field] = _formula_override(cell, canonical[column], column, row_number)

        values["row_id"] = _normalized_row_id(values.get("row_id"), index + 1)
        values["supplier_currency"] = str(values.get("supplier_currency") or "EUR").upper()
        values["sales_currency"] = str(values.get("sales_currency") or "EUR").upper()
        row = CalculatorRow(**values)
        imported.append(row)
        if _row_has_imported_content(row):
            meaningful_indexes.append(index)

    if not meaningful_indexes:
        return (), tuple(warnings)
    last_index = max(meaningful_indexes)
    return tuple(imported[: last_index + 1]), tuple(warnings)


def _field_value(field_name: str, cell: _CellData) -> object:
    if cell.formula:
        if field_name in _TEXT_FIELDS or field_name in _BOOLEAN_FIELDS:
            return cell.value if cell.value is not None else ""
        return unwrap_canonical_export_formula(field_name, cell.formula)
    value = cell.value
    if field_name in _BOOLEAN_FIELDS:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value or "").strip().lower() in {"1", "true", "yes", "x"}
    if field_name in _DATE_FIELDS and isinstance(value, (int, float)):
        return _excel_date_text(value)
    if field_name in _TEXT_FIELDS:
        return "" if value is None else str(value)
    return 0.0 if value is None else value


def _sales_price_value(cell: _CellData, row_number: int) -> object:
    automatic_formulas = {
        f"=Q{row_number}",
        f"=IFERROR(Q{row_number}*W{row_number}/AB{row_number},0)",
    }
    if cell.formula and any(_formula_equal(cell.formula, formula) for formula in automatic_formulas):
        return None
    if cell.formula:
        return cell.formula
    return None if cell.value in (None, "") else cell.value


def _formula_override(
    cell: _CellData,
    canonical_formula: str,
    column: str,
    row_number: int,
) -> object:
    if cell.formula:
        formula_field = _FORMULA_FIELD_BY_COLUMN.get(column, "")
        unwrapped = unwrap_canonical_export_formula(formula_field, cell.formula)
        if unwrapped != cell.formula:
            return unwrapped
        return None if _known_template_formula(cell.formula, canonical_formula, column, row_number) else cell.formula
    return None if cell.value in (None, "") else cell.value


def _known_template_formula(formula: str, canonical_formula: str, column: str, row: int) -> bool:
    candidates = {canonical_formula}
    legacy = {
        "S": f"=Q{row}*R{row}",
        "U": f"=S{row}*(1-T{row})",
        "W": f"=IFERROR(VLOOKUP(V{row},Curr!$B$2:$C$13,2,FALSE),0)",
        "X": f"=U{row}*W{row}",
        "Y": f"=Q{row}",
        "Z": f"=Y{row}*R{row}",
        "AB": f"=IFERROR(VLOOKUP(AA{row},Curr!$B$2:$C$13,2,FALSE),0)",
        "AC": f"=Y{row}*AB{row}*R{row}",
        "AD": f"=AC{row}-X{row}",
        "AE": f"=IFERROR(AD{row}/AC{row},0)",
    }
    if column in legacy:
        candidates.add(legacy[column])
    normalized_formula = _normalize_formula(formula)
    return any(normalized_formula == _normalize_formula(candidate) for candidate in candidates)


def _formula_equal(left: str, right: str) -> bool:
    return _normalize_formula(left) == _normalize_formula(right)


def _normalize_formula(value: str) -> str:
    normalized = re.sub(r"\s+", "", str(value or "")).upper()
    return normalized.replace("=+", "=")


def _normalized_row_id(value: object, fallback: int) -> str:
    if value in (None, ""):
        return str(fallback)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _row_has_imported_content(row: CalculatorRow) -> bool:
    ignored = {"row_id", "supplier_currency", "sales_currency"}
    for field_name, value in row.__dict__.items():
        if field_name in ignored or field_name.endswith("_override"):
            continue
        if isinstance(value, bool):
            if value:
                return True
        elif value not in (None, "", 0, 0.0):
            return True
    return any(value not in (None, "", 0, 0.0) for name, value in row.__dict__.items() if name.endswith("_override"))


def _excel_date_text(value: int | float) -> str:
    try:
        date = datetime(1899, 12, 30) + timedelta(days=float(value))
    except (OverflowError, TypeError, ValueError):
        return str(value)
    return date.date().isoformat()


def _itinerary_name_from_filename(filename: str) -> str:
    stem = Path(str(filename or "")).stem.strip()
    for suffix in (" - Calculation", " Calculation", " - Calculator"):
        if stem.lower().endswith(suffix.lower()):
            stem = stem[: -len(suffix)].rstrip()
            break
    return stem
