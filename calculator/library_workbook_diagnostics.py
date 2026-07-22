"""Stable Local Library diagnostic formatting."""
from __future__ import annotations

from calculator.library_workbook_models import LocalLibraryDiagnostic


def display_value(value: object) -> str:
    if value is None:
        return "<blank>"
    text = str(value)
    if len(text) > 160:
        text = f"{text[:157]}..."
    return repr(text)


def diagnostic(
    *,
    category: str,
    code: str,
    worksheet: str,
    excel_row: int | None,
    field: str,
    value: object,
    reason: str,
) -> LocalLibraryDiagnostic:
    rendered_value = display_value(value)
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
