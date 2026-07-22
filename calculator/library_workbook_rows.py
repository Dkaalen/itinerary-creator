"""Local Library product-row detection and validation."""
from __future__ import annotations

from typing import Mapping

from calculator.library_model import LocalLibraryRow
from calculator.library_workbook_diagnostics import diagnostic
from calculator.library_workbook_models import LocalLibraryDiagnostic


def has_product_content(mapping: Mapping[str, object]) -> bool:
    return bool(str(mapping.get("Travel element") or "").strip() or str(mapping.get("Type") or "").strip())


def row_validation_issue(
    row: LocalLibraryRow,
    sheet: str,
    source_row: int,
    rates: Mapping[str, float],
) -> LocalLibraryDiagnostic | None:
    if not row.type:
        return diagnostic(
            category="invalid_record",
            code="missing_required_value",
            worksheet=sheet,
            excel_row=source_row,
            field="Type",
            value="",
            reason="A product row requires a Type value.",
        )
    if not row.travel_element:
        return diagnostic(
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
            return diagnostic(
                category="invalid_record",
                code="unsupported_currency",
                worksheet=sheet,
                excel_row=source_row,
                field=field,
                value=code,
                reason=f"No valid Curr-sheet rate exists for {code}.",
            )
    return None
