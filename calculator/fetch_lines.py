"""Apply fetched Local Library lines to calculator state."""

from __future__ import annotations

from dataclasses import replace

from calculator.calculator_state import CalculatorState, add_row, next_row_id
from calculator.library_model import LocalLibraryRow
from calculator.library_normalize import library_row_to_calculator_row
from calculator.library_search import search_library_rows
from calculator.row_model import CalculatorRow

_PRESERVED_CONTEXT_FIELDS = ("day", "from_date", "to_date", "from_time", "to_time")
_FETCH_SIGNAL_FIELDS = (
    "type",
    "supplier",
    "url",
    "comments",
    "gross_price_per_unit",
    "units",
    "sales_price_per_unit",
)


def calculator_row_from_library_line(library_row: LocalLibraryRow, row_id: str) -> CalculatorRow:
    """Return a calculator row filled from one Local Library line."""

    return library_row_to_calculator_row(library_row, row_id=row_id)


def fetch_library_line_into_row(
    state: CalculatorState,
    library_row: LocalLibraryRow,
    target_row_id: str | None,
) -> CalculatorState:
    """Fill the selected calculator row from a Local Library row."""

    row_id = target_row_id or next_row_id(state)
    fetched_row = calculator_row_from_library_line(library_row, row_id=row_id)
    if any(row.row_id == row_id for row in state.rows):
        return replace(
            state,
            rows=tuple(fetched_row if row.row_id == row_id else row for row in state.rows),
        )
    return add_row(state, fetched_row)


def fetch_library_line_into_first_available_row(
    state: CalculatorState,
    library_row: LocalLibraryRow,
) -> CalculatorState:
    """Fill the first empty calculator row, or append when no empty row exists."""

    target = next((row for row in state.rows if _row_is_empty(row)), None)
    if target is None:
        return fetch_library_line_into_row(state, library_row, None)
    return fetch_library_line_into_row_preserving_context(state, library_row, target.row_id)


def fetch_library_line_into_row_preserving_context(
    state: CalculatorState,
    library_row: LocalLibraryRow,
    target_row_id: str,
) -> CalculatorState:
    """Fill an existing calculator row while preserving day/date/time context."""

    target = next((row for row in state.rows if row.row_id == target_row_id), None)
    if target is None:
        return fetch_library_line_into_row(state, library_row, target_row_id)
    fetched_row = _merge_fetched_row_with_context(target, library_row)
    return replace(
        state,
        rows=tuple(fetched_row if row.row_id == target_row_id else row for row in state.rows),
    )


def autofill_exact_travel_element_matches(
    state: CalculatorState,
    library_rows: tuple[LocalLibraryRow, ...],
) -> CalculatorState:
    """Fill rows whose typed travel element exactly matches one Local Library line."""

    if not library_rows:
        return state
    updated_rows: list[CalculatorRow] = []
    changed = False
    for row in state.rows:
        match = _exact_travel_element_match(row.travel_element, library_rows)
        if match is None or not _row_can_be_autofilled(row):
            updated_rows.append(row)
            continue
        updated_rows.append(_merge_fetched_row_with_context(row, match))
        changed = True
    if not changed:
        return state
    return replace(state, rows=tuple(updated_rows))


def _exact_travel_element_match(
    travel_element: str,
    library_rows: tuple[LocalLibraryRow, ...],
) -> LocalLibraryRow | None:
    query = str(travel_element or "").strip()
    if len(query) < 3:
        return None
    results = search_library_rows(library_rows, query, limit=3)
    normalized_query = query.casefold().strip()
    exact = [result.row for result in results if result.row.travel_element.casefold().strip() == normalized_query]
    return exact[0] if len(exact) == 1 else None


def _merge_fetched_row_with_context(row: CalculatorRow, library_row: LocalLibraryRow) -> CalculatorRow:
    fetched = calculator_row_from_library_line(library_row, row.row_id)
    preserved = {
        field_name: getattr(row, field_name) or getattr(fetched, field_name)
        for field_name in _PRESERVED_CONTEXT_FIELDS
    }
    return fetched.with_changes(**preserved)


def _row_can_be_autofilled(row: CalculatorRow) -> bool:
    return bool(row.travel_element.strip()) and not any(_has_value(getattr(row, field)) for field in _FETCH_SIGNAL_FIELDS)


def _row_is_empty(row: CalculatorRow) -> bool:
    ignored_fields = {"row_id", "supplier_currency", "sales_currency", *_PRESERVED_CONTEXT_FIELDS}
    for field_name, value in row.__dict__.items():
        if field_name in ignored_fields:
            continue
        if _has_value(value):
            return False
    return True


def _has_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) != 0.0
    return bool(str(value or "").strip())
