"""Patch approved calculator cells directly inside the reference XLSX package.

The workbook is treated as an immutable visual/structural template. Export only
rewrites calculator data, currency lookup values, and canonical formula cells;
every other package part is copied byte-for-byte from the reference workbook.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import re
from typing import Iterable, Mapping
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from calculator.calculator_state import CalculatorState
from calculator.cell_formula_engine import CalculatorCellFormulaEvaluator
from calculator.columns import DATA_END_ROW, DATA_START_ROW
from calculator.currency_rates import normalize_currency_rates
from calculator.formula_map import (
    LEGACY_PAYMENT_CELLS_TO_CLEAR,
    PAYMENT_FORMULAS,
    TOTAL_FORMULAS,
    expected_row_formulas,
)
from calculator.numeric_input import parse_decimal_input_strict
from calculator.row_model import FORMULA_OVERRIDE_FIELD_BY_KEY, CalculatorRow
from calculator.template_structure import default_template_path

_CURR_SHEET_PART = "xl/worksheets/sheet1.xml"
_KALK_SHEET_PART = "xl/worksheets/sheet2.xml"
_WORKBOOK_PART = "xl/workbook.xml"
_QUOTE_CELL = "Z103"
_CURRENCY_START_ROW = 2
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
_FORMULA_FIELD_BY_COLUMN = {
    "S": "gross_price",
    "U": "net_price",
    "W": "supplier_x_rate",
    "X": "net_price_nok",
    "Z": "price",
    "AB": "sales_x_rate",
    "AC": "sales_price_nok_total",
    "AD": "gp_nok",
    "AE": "gp_percent",
}
_NUMERIC_INPUT_FIELDS = {
    "gross_price_per_unit",
    "units",
    "supplier_commission",
    "vat25",
    "vat15",
    "vat12",
    "vat0_domestic",
    "vat0_international",
}
_CELL_RE_TEMPLATE = r'<c\b(?P<attrs>[^>]*?\br="{ref}"[^>]*?)\s*(?:/>|>(?P<body>.*?)</c>)'
_ROW_RE_TEMPLATE = r'(<row\b[^>]*\br="{row}"[^>]*>)(?P<body>.*?)(</row>)'
_REF_RE = re.compile(r'\br="([A-Z]+)(\d+)"')
_TYPE_ATTR_RE = re.compile(r'\s+t="[^"]*"')


@dataclass(frozen=True)
class PackageExportResult:
    """Exact-reference XLSX bytes and the package parts intentionally changed."""

    content: bytes
    changed_parts: tuple[str, ...]


def export_reference_workbook_package(
    state: CalculatorState,
    template_path: str | Path | None = None,
    *,
    currency_rates: Mapping[str, float] | None = None,
) -> PackageExportResult:
    """Clone the reference package and patch only approved worksheet cells."""

    source_path = Path(template_path) if template_path is not None else default_template_path()
    with ZipFile(source_path, "r") as source:
        curr_xml = source.read(_CURR_SHEET_PART).decode("utf-8")
        kalk_xml = source.read(_KALK_SHEET_PART).decode("utf-8")
        workbook_xml = source.read(_WORKBOOK_PART).decode("utf-8")
        normalized_rates = normalize_currency_rates(currency_rates)
        curr_xml = _patch_currency_sheet(curr_xml, normalized_rates)
        kalk_xml = _patch_kalk_sheet(kalk_xml, tuple(state.rows), normalized_rates)
        workbook_xml = _patch_workbook_calculation_properties(workbook_xml)

        buffer = BytesIO()
        with ZipFile(buffer, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == _CURR_SHEET_PART:
                    data = curr_xml.encode("utf-8")
                elif info.filename == _KALK_SHEET_PART:
                    data = kalk_xml.encode("utf-8")
                elif info.filename == _WORKBOOK_PART:
                    data = workbook_xml.encode("utf-8")
                target.writestr(_clone_zip_info(info), data)

    return PackageExportResult(
        content=buffer.getvalue(),
        changed_parts=(_CURR_SHEET_PART, _KALK_SHEET_PART, _WORKBOOK_PART),
    )


def _patch_workbook_calculation_properties(xml: str) -> str:
    """Require Excel to recalculate formulas while preserving workbook metadata."""

    match = re.search(r"<calcPr\b(?P<attrs>[^>]*)/>", xml)
    if not match:
        raise ValueError("Reference workbook is missing calcPr metadata.")
    attrs = match.group("attrs")
    required = {
        "calcMode": "auto",
        "fullCalcOnLoad": "1",
        "forceFullCalc": "1",
    }
    for name, value in required.items():
        pattern = re.compile(rf'\s+{name}="[^"]*"')
        replacement = f' {name}="{value}"'
        if pattern.search(attrs):
            attrs = pattern.sub(replacement, attrs, count=1)
        else:
            attrs += replacement
    replacement = f"<calcPr{attrs}/>"
    return xml[: match.start()] + replacement + xml[match.end() :]


def _patch_currency_sheet(xml: str, rates: Mapping[str, float]) -> str:
    items = tuple(rates.items())
    for offset in range(12):
        row_number = _CURRENCY_START_ROW + offset
        if offset < len(items):
            code, rate = items[offset]
            xml = _set_cell(xml, f"B{row_number}", str(code).upper(), value_kind="text")
            xml = _set_cell(xml, f"C{row_number}", rate, value_kind="number")
        else:
            xml = _set_cell(xml, f"B{row_number}", None)
            xml = _set_cell(xml, f"C{row_number}", None)
    return re.sub(r'<dimension\s+ref="[^"]+"\s*/>', '<dimension ref="B1:C13"/>', xml, count=1)


def _patch_kalk_sheet(
    xml: str,
    rows: tuple[CalculatorRow, ...],
    currency_rates: Mapping[str, float],
) -> str:
    evaluator = CalculatorCellFormulaEvaluator(rows, currency_rates)
    for row_offset, row_number in enumerate(range(DATA_START_ROW, DATA_END_ROW + 1)):
        row = rows[row_offset] if row_offset < len(rows) else None
        xml = _patch_data_row(xml, row_number, row, evaluator)

    formulas = {**TOTAL_FORMULAS, **PAYMENT_FORMULAS, _QUOTE_CELL: "=Z101"}
    for ref, formula in formulas.items():
        xml = _set_cell(xml, ref, formula, value_kind="formula")
    for ref in LEGACY_PAYMENT_CELLS_TO_CLEAR:
        xml = _set_cell(xml, ref, None)
    return xml


def _patch_data_row(
    xml: str,
    row_number: int,
    row: CalculatorRow | None,
    evaluator: CalculatorCellFormulaEvaluator,
) -> str:
    for column, field_name in _ROW_VALUE_COLUMNS.items():
        value = None if row is None else _row_cell_value(row, field_name)
        kind = _row_value_kind(field_name, value)
        xml = _set_cell(xml, f"{column}{row_number}", value, value_kind=kind)

    if row is None:
        sales_value: object = f"=Q{row_number}"
    else:
        sales_value = _sales_price_cell_value(row, row_number, evaluator)
    xml = _set_cell(xml, f"Y{row_number}", sales_value, value_kind=_numeric_or_formula_kind(sales_value))

    canonical = expected_row_formulas(row_number)
    for column, formula in canonical.items():
        if column == "Y":
            continue
        value: object = formula
        if row is not None:
            field_name = _FORMULA_FIELD_BY_COLUMN.get(column, "")
            override_field = FORMULA_OVERRIDE_FIELD_BY_KEY.get(field_name, "")
            override_value = getattr(row, override_field, None) if override_field else None
            if override_value is not None:
                value = override_value
        xml = _set_cell(xml, f"{column}{row_number}", value, value_kind=_numeric_or_formula_kind(value))
    return xml


def _row_cell_value(row: CalculatorRow, field_name: str) -> object:
    value = getattr(row, field_name)
    if field_name == "row_id" and not value:
        return None
    if field_name in {"supplier_currency", "sales_currency"}:
        return str(value or "EUR").upper()
    return value


def _row_value_kind(field_name: str, value: object) -> str:
    if value in (None, ""):
        return "blank"
    if field_name in {"manual_booking", "non_refundable", "refundable"}:
        return "boolean"
    if field_name in _NUMERIC_INPUT_FIELDS:
        return _numeric_or_formula_kind(value)
    return "text"


def _sales_price_cell_value(
    row: CalculatorRow,
    row_number: int,
    evaluator: CalculatorCellFormulaEvaluator,
) -> object:
    value = row.sales_price_per_unit
    if value in (None, ""):
        return f"=Q{row_number}"
    parsed = evaluator.evaluate_expression(value, current_cell=f"Y{row_number}")
    gross = evaluator.evaluate_cell(f"Q{row_number}")
    if parsed == 0 and gross > 0:
        return f"=Q{row_number}"
    return value


def _numeric_or_formula_kind(value: object) -> str:
    if value in (None, ""):
        return "blank"
    if isinstance(value, str) and value.strip().startswith("="):
        return "formula"
    return "number"


def _set_cell(xml: str, ref: str, value: object, *, value_kind: str = "blank") -> str:
    pattern = re.compile(_CELL_RE_TEMPLATE.format(ref=re.escape(ref)), re.DOTALL)
    match = pattern.search(xml)
    fragment = _cell_fragment(ref, match.group("attrs") if match else f' r="{ref}"', value, value_kind)
    if match:
        return xml[: match.start()] + fragment + xml[match.end() :]
    if value is None and value_kind == "blank":
        return xml
    return _insert_cell(xml, ref, fragment)


def _cell_fragment(ref: str, attrs: str, value: object, value_kind: str) -> str:
    clean_attrs = _TYPE_ATTR_RE.sub("", attrs).rstrip().rstrip("/")
    if f'r="{ref}"' not in clean_attrs:
        clean_attrs = f' r="{ref}"' + clean_attrs
    if value is None or value_kind == "blank":
        return f"<c{clean_attrs}/>"
    if value_kind == "text":
        text = escape(str(value), {'"': "&quot;"})
        return f'<c{clean_attrs} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'
    if value_kind == "boolean":
        return f'<c{clean_attrs} t="b"><v>{1 if bool(value) else 0}</v></c>'
    if value_kind == "formula":
        formula = escape(str(value).strip().lstrip("="))
        return f"<c{clean_attrs}><f>{formula}</f></c>"
    return f"<c{clean_attrs}><v>{_number_text(value)}</v></c>"


def _insert_cell(xml: str, ref: str, fragment: str) -> str:
    row_number = int(re.search(r"\d+$", ref).group())
    row_pattern = re.compile(_ROW_RE_TEMPLATE.format(row=row_number), re.DOTALL)
    row_match = row_pattern.search(xml)
    if not row_match:
        return _insert_missing_row(xml, row_number, fragment)
    body = row_match.group("body")
    target_column = _column_number(re.match(r"[A-Z]+", ref).group())
    insertion = len(body)
    for cell_match in re.finditer(r'<c\b[^>]*\br="([A-Z]+)\d+"[^>]*(?:/>|>.*?</c>)', body, re.DOTALL):
        if _column_number(cell_match.group(1)) > target_column:
            insertion = cell_match.start()
            break
    new_body = body[:insertion] + fragment + body[insertion:]
    replacement = row_match.group(1) + new_body + row_match.group(3)
    return xml[: row_match.start()] + replacement + xml[row_match.end() :]


def _insert_missing_row(xml: str, row_number: int, fragment: str) -> str:
    sheet_data_match = re.search(r'(<sheetData>)(?P<body>.*?)(</sheetData>)', xml, re.DOTALL)
    if not sheet_data_match:
        raise ValueError("Reference workbook is missing sheetData.")
    body = sheet_data_match.group("body")
    new_row = f'<row r="{row_number}">{fragment}</row>'
    insertion = len(body)
    for row_match in re.finditer(r'<row\b[^>]*\br="(\d+)"[^>]*>.*?</row>', body, re.DOTALL):
        if int(row_match.group(1)) > row_number:
            insertion = row_match.start()
            break
    new_body = body[:insertion] + new_row + body[insertion:]
    replacement = sheet_data_match.group(1) + new_body + sheet_data_match.group(3)
    return xml[: sheet_data_match.start()] + replacement + xml[sheet_data_match.end() :]


def _number_text(value: object) -> str:
    decimal = parse_decimal_input_strict(value, allow_blank=False)
    assert decimal is not None
    text = format(decimal, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _column_number(letters: str) -> int:
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - ord("A") + 1
    return value


def _clone_zip_info(info: ZipInfo) -> ZipInfo:
    clone = ZipInfo(info.filename, date_time=info.date_time)
    clone.compress_type = info.compress_type if info.compress_type is not None else ZIP_DEFLATED
    clone.comment = info.comment
    clone.extra = info.extra
    clone.internal_attr = info.internal_attr
    clone.external_attr = info.external_attr
    clone.create_system = info.create_system
    clone.create_version = info.create_version
    clone.extract_version = info.extract_version
    clone.flag_bits = info.flag_bits
    clone.volume = info.volume
    return clone
