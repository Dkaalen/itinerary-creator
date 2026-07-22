"""Formula XML and cached-value inspection for the Local Library workbook."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from xml.etree.ElementTree import iterparse
from zipfile import ZipFile

from openpyxl.formula import Tokenizer
from openpyxl.utils.cell import column_index_from_string

from calculator.library_workbook_diagnostics import diagnostic
from calculator.library_workbook_models import FormulaCell, LocalLibraryDiagnostic
from calculator.library_workbook_schema import DATA_SHEETS

_EXTERNAL_WORKBOOK_REFERENCE_RE = re.compile(r"\[[^\]]+\]")
_CELL_ROW_REFERENCE_RE = re.compile(r"(?<![A-Za-z0-9_])(?P<column>\$?[A-Z]{1,3}\$?)\d+")
_CELL_COORDINATE_RE = re.compile(r"(?P<column>[A-Z]+)(?P<row>\d+)")
_SPREADSHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def read_formula_cells(path: Path, workbook: object) -> dict[str, dict[int, tuple[FormulaCell, ...]]]:
    worksheet_paths = {
        sheet.title: sheet._worksheet_path
        for sheet in workbook.worksheets  # type: ignore[attr-defined]
        if sheet.title in DATA_SHEETS
    }
    result: dict[str, dict[int, tuple[FormulaCell, ...]]] = {}
    with ZipFile(path, "r") as package:
        for sheet_name, worksheet_path in worksheet_paths.items():
            result[sheet_name] = read_sheet_formula_cells(package, worksheet_path)
    return result


def read_sheet_formula_cells(package: ZipFile, worksheet_path: str) -> dict[int, tuple[FormulaCell, ...]]:
    raw_cells: list[tuple[int, int, str | None, str, str | None, bool]] = []
    shared_formulas: dict[str, str] = {}
    with package.open(worksheet_path) as source:
        for _, element in iterparse(source, events=("end",)):
            if element.tag != f"{_SPREADSHEET_NS}c":
                continue
            formula_element = element.find(f"{_SPREADSHEET_NS}f")
            if formula_element is not None:
                coordinate = str(element.attrib.get("r") or "")
                match = _CELL_COORDINATE_RE.fullmatch(coordinate)
                if match is not None:
                    row_number = int(match.group("row"))
                    column_index = column_index_from_string(match.group("column"))
                    formula_body = formula_element.text
                    shared_id = str(formula_element.attrib.get("si") or "")
                    if formula_body and shared_id:
                        shared_formulas[shared_id] = formula_body
                    value_element = element.find(f"{_SPREADSHEET_NS}v")
                    cached_value = value_element.text if value_element is not None else None
                    raw_cells.append((
                        row_number,
                        column_index,
                        formula_body,
                        shared_id,
                        cached_value,
                        element.attrib.get("t") == "e",
                    ))
            element.clear()

    by_row: dict[int, list[FormulaCell]] = {}
    for row_number, column_index, formula_body, shared_id, cached_value, cached_error in raw_cells:
        resolved_formula = formula_body or shared_formulas.get(shared_id, "")
        formula = f"={resolved_formula}" if resolved_formula else ""
        by_row.setdefault(row_number, []).append(
            FormulaCell(column_index, formula, cached_value, cached_error)
        )
    return {row_number: tuple(cells) for row_number, cells in by_row.items()}


def formula_and_cached_value_issues(
    headers: tuple[str, ...],
    formula_cells: tuple[FormulaCell, ...],
    worksheet: str,
    excel_row: int,
) -> tuple[LocalLibraryDiagnostic, ...]:
    issues: list[LocalLibraryDiagnostic] = []
    for formula_cell in formula_cells:
        header_index = formula_cell.column_index - 1
        header = headers[header_index] if 0 <= header_index < len(headers) else ""
        if not header:
            continue
        formula_value = formula_cell.formula
        if not formula_value:
            issues.append(diagnostic(
                category="invalid_record", code="invalid_formula", worksheet=worksheet,
                excel_row=excel_row, field=header, value="",
                reason="Shared formula has no master formula definition.",
            ))
            continue
        if not formula_syntax_is_plausible(formula_value):
            issues.append(diagnostic(
                category="invalid_record", code="invalid_formula", worksheet=worksheet,
                excel_row=excel_row, field=header, value=formula_value,
                reason="Formula syntax is incomplete or unbalanced.",
            ))
            continue
        if formula_cell.cached_value in (None, "") or formula_cell.cached_error:
            reason = "Formula cached value is an Excel error." if formula_cell.cached_error else "Formula has no cached value."
            issues.append(diagnostic(
                category="invalid_record", code="invalid_formula_cache", worksheet=worksheet,
                excel_row=excel_row, field=header, value=formula_cell.cached_value, reason=reason,
            ))
            continue
        if _EXTERNAL_WORKBOOK_REFERENCE_RE.search(formula_value):
            issues.append(diagnostic(
                category="warning", code="external_formula_reference", worksheet=worksheet,
                excel_row=excel_row, field=header, value=formula_value,
                reason="Formula references another workbook; the cached value was used.",
            ))
    return tuple(issues)


def formula_syntax_is_plausible(formula: str) -> bool:
    canonical_formula = _CELL_ROW_REFERENCE_RE.sub(r"\g<column>1", formula)
    return canonical_formula_syntax_is_plausible(canonical_formula)


@lru_cache(maxsize=512)
def canonical_formula_syntax_is_plausible(formula: str) -> bool:
    try:
        tokens = Tokenizer(formula).items
    except Exception:
        return False
    if not tokens:
        return False
    depth = 0
    for token in tokens:
        if token.type in {"FUNC", "PAREN"} and token.subtype == "OPEN":
            depth += 1
        elif token.type in {"FUNC", "PAREN"} and token.subtype == "CLOSE":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0
