"""Apply fetched Local Library lines to calculator state."""

from __future__ import annotations

from dataclasses import replace

from calculator.calculator_state import CalculatorState, add_row, next_row_id
from calculator.library_model import LocalLibraryRow
from calculator.library_normalize import library_row_to_calculator_row
from calculator.row_model import CalculatorRow


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
