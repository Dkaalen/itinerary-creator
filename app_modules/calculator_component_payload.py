"""Build payloads for the browser-side calculator grid component."""

from __future__ import annotations

from typing import Any

from app_modules.calculator_grid_data import rows_to_table_data
from calculator.calculations import DEFAULT_CURRENCY_RATES
from calculator.calculator_state import CalculatorState
from calculator.library_model import LocalLibraryRow
from calculator.library_search import library_result_label, library_result_preview
from calculator.library_store import LocalLibraryReadResult
from calculator.library_normalize import library_row_to_calculator_row


def build_calculator_grid_payload(
    state: CalculatorState,
    library_read: LocalLibraryReadResult,
    *,
    show_advanced: bool = False,
) -> dict[str, Any]:
    """Return the JSON-serializable component payload for the calculator grid."""

    return {
        "itinerary_name": state.itinerary_name,
        "rows": rows_to_table_data(state.rows, show_advanced=True),
        "show_advanced": show_advanced,
        "currency_rates": dict(DEFAULT_CURRENCY_RATES),
        "library_status": _library_read_status(library_read),
        "library_rows": [_library_row_payload(row) for row in library_read.rows if row.is_available_for_fetch],
    }


def _library_row_payload(row: LocalLibraryRow) -> dict[str, Any]:
    calculator_row = library_row_to_calculator_row(row, row_id="")
    table_row = rows_to_table_data((calculator_row,), show_advanced=True)[0]
    return {
        "library_id": row.library_id,
        "label": library_result_label(row),
        "preview": _compact_preview(row),
        "row_data": table_row,
        "travel_element": row.travel_element,
        "supplier": row.supplier,
        "country": row.country,
        "category": row.category,
        "type": row.type,
        "comments": row.comments,
        "search_text": row.search_text,
        "url": row.url,
    }


def _library_read_status(read_result: LocalLibraryReadResult) -> str:
    fetchable_count = sum(1 for row in read_result.rows if row.is_available_for_fetch)
    if read_result.source == "google_sheets" and not read_result.read_only:
        return f"Google Sheets connected ({fetchable_count} fetchable lines)."
    message = read_result.message or "Using bundled read-only Local Library fixture."
    return f"{message} ({fetchable_count} fallback lines)."


def _compact_preview(row: LocalLibraryRow) -> str:
    return library_result_preview(row).replace("\n", " • ")[:450]
