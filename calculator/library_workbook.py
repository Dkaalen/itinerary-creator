"""Validated repository-local Excel Local Library loader."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Iterable, Mapping
from xml.etree.ElementTree import iterparse
from zipfile import ZipFile

from openpyxl import load_workbook
from openpyxl.formula import Tokenizer
from openpyxl.utils.cell import column_index_from_string

from calculator.library_model import LocalLibraryRow
from calculator.library_normalize import LocalLibraryNumericValueError, normalize_library_mapping
from calculator.numeric_input import parse_decimal_input_strict

WORKBOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "Calculation-template-Inputs-fixed-outline-restored.xlsx"
)
REQUIRED_SHEETS = ("Curr", "General", "Hotels", "Transfers", "Transport", "Activities")
DATA_SHEETS = REQUIRED_SHEETS[1:]
_REQUIRED_HEADERS = {
    "ID",
    "Type",
    "Travel element",
    "Gross P per unit",
    "Supp Comm",
    "Supp curr",
    "Sales P per unit",
    "Sales curr",
}
_EXTERNAL_WORKBOOK_REFERENCE_RE = re.compile(r"\[[^\]]+\]")
_CELL_ROW_REFERENCE_RE = re.compile(r"(?<![A-Za-z0-9_])(?P<column>\$?[A-Z]{1,3}\$?)\d+")
_CELL_COORDINATE_RE = re.compile(r"(?P<column>[A-Z]+)(?P<row>\d+)")
_SPREADSHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass(frozen=True)
class LocalLibraryDiagnostic:
    """One actionable non-fatal Local Library workbook issue."""

    category: str
    code: str
    message: str
    worksheet: str = ""
    excel_row: int | None = None
    field: str = ""
    value: str = ""


class LocalLibraryWorkbookError(RuntimeError):
    """Raised when the bundled Local Library workbook is unusable."""

    def __init__(
        self,
        message: str,
        *,
        category: str = "fatal_workbook",
        code: str = "workbook_unusable",
        diagnostics: tuple[LocalLibraryDiagnostic, ...] = (),
    ) -> None:
        super().__init__(message)
        self.category = category
        self.code = code
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class LocalLibraryWorkbook:
    rows: tuple[LocalLibraryRow, ...]
    currency_rates: Mapping[str, float]
    path: Path
    fingerprint: str
    diagnostics: tuple[LocalLibraryDiagnostic, ...] = ()

    @property
    def invalid_records(self) -> tuple[LocalLibraryDiagnostic, ...]:
        return tuple(issue for issue in self.diagnostics if issue.category == "invalid_record")

    @property
    def warnings(self) -> tuple[LocalLibraryDiagnostic, ...]:
        return tuple(issue for issue in self.diagnostics if issue.category == "warning")


@dataclass(frozen=True)
class _FormulaCell:
    column_index: int
    formula: str
    cached_value: str | None
    cached_error: bool


@lru_cache(maxsize=4)
def _load_cached(path_text: str, modified_ns: int, size: int) -> LocalLibraryWorkbook:
    path = Path(path_text)
    workbook = None
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
        _validate_required_sheets(workbook.sheetnames)
        formula_cells = _read_formula_cells(path, workbook)

        rates, currency_diagnostics = _currency_rates(workbook["Curr"])
        diagnostics: list[LocalLibraryDiagnostic] = list(currency_diagnostics)
        rows: list[LocalLibraryRow] = []

        for sheet_name in DATA_SHEETS:
            sheet = workbook[sheet_name]
            headers, header_row = _headers(sheet)
            missing_headers = sorted(_REQUIRED_HEADERS - set(headers))
            if missing_headers:
                raise LocalLibraryWorkbookError(
                    f"{sheet_name} is missing required header(s): {', '.join(missing_headers)}",
                    category="schema",
                    code="missing_headers",
                )

            for source_row, value_cells in enumerate(
                sheet.iter_rows(min_row=header_row + 1),
                start=header_row + 1,
            ):
                values = tuple(cell.value for cell in value_cells)
                mapping = {header: value for header, value in zip(headers, values) if header}
                if not _has_product_content(mapping):
                    continue

                row_issues = _formula_and_cached_value_issues(
                    headers,
                    formula_cells.get(sheet_name, {}).get(source_row, ()),
                    sheet_name,
                    source_row,
                )
                diagnostics.extend(row_issues)
                if any(issue.category == "invalid_record" for issue in row_issues):
                    continue

                enriched = dict(mapping)
                enriched.update(
                    {
                        "schema_version": "local_library_v1",
                        "source_workbook": path.name,
                        "source_sheet": sheet_name,
                        "source_row": source_row,
                        "country": str(mapping.get("ID") or "").strip(),
                        "category": sheet_name,
                        "record_type": "line",
                        "is_deleted": False,
                        "is_fetchable": True,
                    }
                )
                try:
                    row = normalize_library_mapping(enriched, strict_numeric=True)
                except LocalLibraryNumericValueError as error:
                    diagnostics.append(
                        _diagnostic(
                            category="invalid_record",
                            code="invalid_numeric_value",
                            worksheet=sheet_name,
                            excel_row=source_row,
                            field=error.source_field or error.field_name,
                            value=error.value,
                            reason=error.reason,
                        )
                    )
                    continue

                validation_issue = _row_validation_issue(row, sheet_name, source_row, rates)
                if validation_issue is not None:
                    diagnostics.append(validation_issue)
                    continue
                rows.append(row)

        if not rows:
            raise LocalLibraryWorkbookError(
                "Local Library workbook contains no fetchable rows.",
                category="fatal_workbook",
                code="no_fetchable_rows",
                diagnostics=tuple(diagnostics),
            )
        fingerprint = f"{modified_ns:x}-{size:x}"
        return LocalLibraryWorkbook(tuple(rows), rates, path, fingerprint, tuple(diagnostics))
    except LocalLibraryWorkbookError:
        raise
    except Exception as exc:
        raise LocalLibraryWorkbookError(
            f"Local Library workbook is corrupt or unreadable: {path.name}",
            category="fatal_workbook",
            code="unreadable_workbook",
        ) from exc
    finally:
        if workbook is not None:
            workbook.close()


def load_local_library_workbook(path: str | Path = WORKBOOK_PATH) -> LocalLibraryWorkbook:
    workbook_path = Path(path)
    if not workbook_path.is_file():
        raise LocalLibraryWorkbookError(
            f"Local Library workbook is missing: {workbook_path}",
            category="fatal_workbook",
            code="missing_workbook",
        )
    stat = workbook_path.stat()
    return _load_cached(str(workbook_path.resolve()), stat.st_mtime_ns, stat.st_size)


def clear_local_library_workbook_cache() -> None:
    _load_cached.cache_clear()


def _validate_required_sheets(sheet_names: Iterable[object]) -> None:
    names = tuple(str(name) for name in sheet_names)
    missing = [name for name in REQUIRED_SHEETS if name not in names]
    if missing:
        raise LocalLibraryWorkbookError(
            f"Local Library workbook is missing required sheet(s): {', '.join(missing)}",
            category="schema",
            code="missing_sheets",
        )


def _headers(sheet) -> tuple[tuple[str, ...], int]:
    for row_number, row in enumerate(sheet.iter_rows(min_row=1, max_row=12, values_only=True), start=1):
        headers = tuple(str(value).strip() if value is not None else "" for value in row)
        if "Travel element" in headers and "Type" in headers:
            return headers, row_number
    raise LocalLibraryWorkbookError(
        f"{sheet.title} has no recognizable Calculator header row.",
        category="schema",
        code="missing_header_row",
    )


def _currency_rates(sheet) -> tuple[dict[str, float], tuple[LocalLibraryDiagnostic, ...]]:
    rates = {"NOK": 1.0}
    diagnostics: list[LocalLibraryDiagnostic] = []
    for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        code = str(row[1] or "").strip().upper() if len(row) > 1 else ""
        value = row[2] if len(row) > 2 else None
        if not code:
            continue
        try:
            parsed = parse_decimal_input_strict(value, allow_blank=False)
            assert parsed is not None
            rate = float(parsed)
            if rate <= 0:
                raise ValueError("Currency rate must be positive.")
        except (ValueError, TypeError):
            diagnostics.append(
                _diagnostic(
                    category="warning",
                    code="invalid_currency_rate",
                    worksheet="Curr",
                    excel_row=row_number,
                    field="Rate",
                    value=value,
                    reason=f"The rate for {code} is not a positive finite number and was ignored.",
                )
            )
            continue
        if code in rates and rates[code] != rate:
            diagnostics.append(
                _diagnostic(
                    category="warning",
                    code="duplicate_currency_rate",
                    worksheet="Curr",
                    excel_row=row_number,
                    field="Currency",
                    value=code,
                    reason=f"A later valid rate replaced the earlier {code} rate.",
                )
            )
        rates[code] = rate
    return rates, tuple(diagnostics)


def _read_formula_cells(path: Path, workbook: object) -> dict[str, dict[int, tuple[_FormulaCell, ...]]]:
    worksheet_paths = {
        sheet.title: sheet._worksheet_path
        for sheet in workbook.worksheets  # type: ignore[attr-defined]
        if sheet.title in DATA_SHEETS
    }
    result: dict[str, dict[int, tuple[_FormulaCell, ...]]] = {}
    with ZipFile(path, "r") as package:
        for sheet_name, worksheet_path in worksheet_paths.items():
            result[sheet_name] = _read_sheet_formula_cells(package, worksheet_path)
    return result


def _read_sheet_formula_cells(
    package: ZipFile,
    worksheet_path: str,
) -> dict[int, tuple[_FormulaCell, ...]]:
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
                    cached_error = element.attrib.get("t") == "e"
                    raw_cells.append(
                        (
                            row_number,
                            column_index,
                            formula_body,
                            shared_id,
                            cached_value,
                            cached_error,
                        )
                    )
            element.clear()

    by_row: dict[int, list[_FormulaCell]] = {}
    for row_number, column_index, formula_body, shared_id, cached_value, cached_error in raw_cells:
        resolved_formula = formula_body or shared_formulas.get(shared_id, "")
        formula = f"={resolved_formula}" if resolved_formula else ""
        by_row.setdefault(row_number, []).append(
            _FormulaCell(
                column_index=column_index,
                formula=formula,
                cached_value=cached_value,
                cached_error=cached_error,
            )
        )
    return {row_number: tuple(cells) for row_number, cells in by_row.items()}


def _formula_and_cached_value_issues(
    headers: tuple[str, ...],
    formula_cells: tuple[_FormulaCell, ...],
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
            issues.append(
                _diagnostic(
                    category="invalid_record",
                    code="invalid_formula",
                    worksheet=worksheet,
                    excel_row=excel_row,
                    field=header,
                    value="",
                    reason="Shared formula has no master formula definition.",
                )
            )
            continue
        if not _formula_syntax_is_plausible(formula_value):
            issues.append(
                _diagnostic(
                    category="invalid_record",
                    code="invalid_formula",
                    worksheet=worksheet,
                    excel_row=excel_row,
                    field=header,
                    value=formula_value,
                    reason="Formula syntax is incomplete or unbalanced.",
                )
            )
            continue
        if formula_cell.cached_value in (None, "") or formula_cell.cached_error:
            reason = (
                "Formula cached value is an Excel error."
                if formula_cell.cached_error
                else "Formula has no cached value."
            )
            issues.append(
                _diagnostic(
                    category="invalid_record",
                    code="invalid_formula_cache",
                    worksheet=worksheet,
                    excel_row=excel_row,
                    field=header,
                    value=formula_cell.cached_value,
                    reason=reason,
                )
            )
            continue
        if _EXTERNAL_WORKBOOK_REFERENCE_RE.search(formula_value):
            issues.append(
                _diagnostic(
                    category="warning",
                    code="external_formula_reference",
                    worksheet=worksheet,
                    excel_row=excel_row,
                    field=header,
                    value=formula_value,
                    reason="Formula references another workbook; the cached value was used.",
                )
            )
    return tuple(issues)


def _formula_syntax_is_plausible(formula: str) -> bool:
    canonical_formula = _CELL_ROW_REFERENCE_RE.sub(r"\g<column>1", formula)
    return _canonical_formula_syntax_is_plausible(canonical_formula)


@lru_cache(maxsize=512)
def _canonical_formula_syntax_is_plausible(formula: str) -> bool:
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


def _has_product_content(mapping: Mapping[str, object]) -> bool:
    return bool(str(mapping.get("Travel element") or "").strip() or str(mapping.get("Type") or "").strip())


def _row_validation_issue(
    row: LocalLibraryRow,
    sheet: str,
    source_row: int,
    rates: Mapping[str, float],
) -> LocalLibraryDiagnostic | None:
    if not row.type:
        return _diagnostic(
            category="invalid_record",
            code="missing_required_value",
            worksheet=sheet,
            excel_row=source_row,
            field="Type",
            value="",
            reason="A product row requires a Type value.",
        )
    if not row.travel_element:
        return _diagnostic(
            category="invalid_record",
            code="missing_required_value",
            worksheet=sheet,
            excel_row=source_row,
            field="Travel element",
            value="",
            reason="A product row requires a Travel element value.",
        )
    for field, code in (("Supp curr", row.supplier_currency), ("Sales curr", row.sales_currency)):
        if code and code not in rates:
            return _diagnostic(
                category="invalid_record",
                code="unsupported_currency",
                worksheet=sheet,
                excel_row=source_row,
                field=field,
                value=code,
                reason=f"No valid Curr-sheet rate exists for {code}.",
            )
    return None


def _diagnostic(
    *,
    category: str,
    code: str,
    worksheet: str,
    excel_row: int | None,
    field: str,
    value: object,
    reason: str,
) -> LocalLibraryDiagnostic:
    rendered_value = _display_value(value)
    location = f"{worksheet} row {excel_row}" if excel_row is not None else worksheet
    message = f"{location}, {field}: {rendered_value}. {reason}"
    return LocalLibraryDiagnostic(
        category=category,
        code=code,
        message=message,
        worksheet=worksheet,
        excel_row=excel_row,
        field=field,
        value=rendered_value,
    )


def _display_value(value: object) -> str:
    if value is None:
        return "<blank>"
    text = str(value)
    if len(text) > 160:
        text = f"{text[:157]}..."
    return repr(text)
