"""Local Library workbook schema and currency-rate validation."""
from __future__ import annotations

from typing import Iterable

from calculator.library_workbook_diagnostics import diagnostic
from calculator.library_workbook_models import LocalLibraryDiagnostic, LocalLibraryWorkbookError
from calculator.numeric_input import parse_decimal_input_strict

REQUIRED_SHEETS = ("Curr", "General", "Hotels", "Transfers", "Transport", "Activities")
DATA_SHEETS = REQUIRED_SHEETS[1:]
REQUIRED_HEADERS = {
    "ID",
    "Type",
    "Travel element",
    "Gross P per unit",
    "Supp Comm",
    "Supp curr",
    "Sales P per unit",
    "Sales curr",
}


def validate_required_sheets(sheet_names: Iterable[object]) -> None:
    names = tuple(str(name) for name in sheet_names)
    missing = [name for name in REQUIRED_SHEETS if name not in names]
    if missing:
        raise LocalLibraryWorkbookError(
            f"Local Library workbook is missing required sheet(s): {', '.join(missing)}",
            category="schema",
            code="missing_sheets",
        )


def headers(sheet) -> tuple[tuple[str, ...], int]:
    for row_number, row in enumerate(sheet.iter_rows(min_row=1, max_row=12, values_only=True), start=1):
        values = tuple(str(value).strip() if value is not None else "" for value in row)
        if "Travel element" in values and "Type" in values:
            return values, row_number
    raise LocalLibraryWorkbookError(
        f"{sheet.title} has no recognizable Calculator header row.",
        category="schema",
        code="missing_header_row",
    )


def currency_rates(sheet) -> tuple[dict[str, float], tuple[LocalLibraryDiagnostic, ...]]:
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
                diagnostic(
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
                diagnostic(
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
