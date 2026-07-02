"""Build payloads for the browser-side calculator grid component."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from app_modules.calculator_grid_data import rows_to_table_data
from calculator.currency_rates import DEFAULT_CURRENCY_RATES, normalize_currency_rates
from calculator.calculator_state import CalculatorState
from calculator.library_model import LocalLibraryRow
from calculator.library_read_summary import summarize_local_library_read
from calculator.library_search import library_result_label, library_result_preview
from calculator.library_store import LocalLibraryReadResult
from calculator.library_normalize import library_row_to_calculator_row


def build_calculator_grid_payload(
    state: CalculatorState,
    library_read: LocalLibraryReadResult,
    *,
    show_advanced: bool = False,
    currency_rates: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Return the JSON-serializable component payload for the calculator grid."""

    active_rates = normalize_currency_rates(currency_rates)
    return {
        "itinerary_name": state.itinerary_name,
        "rows": rows_to_table_data(state.rows, show_advanced=True, currency_rates=active_rates),
        "state_revision": _calculator_state_revision(state, active_rates),
        "show_advanced": show_advanced,
        "currency_rates": active_rates,
        "library_status": _library_read_status(library_read),
        "library_source": library_read.source,
        "library_read_only": library_read.read_only,
        "library_message": library_read.message,
        "library_rows": [_library_row_payload(row, active_rates) for row in _autocomplete_rows(library_read)],
    }


def _calculator_state_revision(state: CalculatorState, currency_rates: Mapping[str, float]) -> str:
    """Return a stable row-state revision for browser draft protection."""

    payload = {
        "rows": rows_to_table_data(state.rows, show_advanced=True, currency_rates=currency_rates),
        "currency_rates": dict(currency_rates),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _library_row_payload(row: LocalLibraryRow, currency_rates: Mapping[str, float]) -> dict[str, Any]:
    calculator_row = library_row_to_calculator_row(row, row_id="")
    table_row = rows_to_table_data((calculator_row,), show_advanced=True, currency_rates=currency_rates)[0]
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
    return summarize_local_library_read(read_result).component_text


def _compact_preview(row: LocalLibraryRow) -> str:
    return library_result_preview(row).replace("\n", " • ")[:450]



def _autocomplete_rows(read_result: LocalLibraryReadResult) -> tuple[LocalLibraryRow, ...]:
    """Return rows available to the browser autocomplete.

    Google Sheets keeps the explicit fetchable filter. The bundled Cheat Sheet fallback
    also includes section/header rows because users need the whole 501-item cheat sheet
    searchable while offline/read-only.
    """

    if read_result.source == "fixture":
        return tuple(row for row in read_result.rows if not row.is_deleted and (row.search_text or row.travel_element))
    return tuple(row for row in read_result.rows if row.is_available_for_fetch)
