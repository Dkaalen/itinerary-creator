"""State container and row operations for the calculator."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from calculator.defaults import DEFAULT_CALCULATOR_ROW_COUNT
from calculator.row_model import CalculatorRow


@dataclass(frozen=True)
class CalculatorState:
    """Current in-app calculator state independent of Streamlit."""

    itinerary_name: str = ""
    rows: tuple[CalculatorRow, ...] = ()

    def with_itinerary_name(self, itinerary_name: str) -> "CalculatorState":
        """Return a copy with a new itinerary name."""

        return replace(self, itinerary_name=itinerary_name)


def create_calculator_state(itinerary_name: str = "") -> CalculatorState:
    """Create an empty calculator state."""

    return CalculatorState(itinerary_name=itinerary_name)


def create_initial_calculator_state(
    itinerary_name: str = "",
    *,
    row_count: int = DEFAULT_CALCULATOR_ROW_COUNT,
) -> CalculatorState:
    """Create a startup calculator state with blank editable rows."""

    return add_rows(create_calculator_state(itinerary_name), row_count)


def add_row(state: CalculatorState, row: CalculatorRow | None = None) -> CalculatorState:
    """Append a row and assign a stable row id when missing."""

    new_row = row or CalculatorRow()
    if not new_row.row_id:
        new_row = new_row.with_changes(row_id=next_row_id(state))
    return replace(state, rows=(*state.rows, new_row))


def add_rows(state: CalculatorState, count: int) -> CalculatorState:
    """Append several blank rows and return the updated state."""

    updated = state
    for _ in range(max(0, int(count))):
        updated = add_row(updated)
    return updated


def update_row(state: CalculatorState, row_id: str, **changes: Any) -> CalculatorState:
    """Update one row by row id."""

    return replace(
        state,
        rows=tuple(
            row.with_changes(**changes) if row.row_id == row_id else row
            for row in state.rows
        ),
    )


def delete_row(state: CalculatorState, row_id: str) -> CalculatorState:
    """Delete one row by row id."""

    return replace(state, rows=tuple(row for row in state.rows if row.row_id != row_id))


def duplicate_row(state: CalculatorState, row_id: str) -> CalculatorState:
    """Duplicate one row and insert the copy after the original."""

    new_rows: list[CalculatorRow] = []
    duplicate_id = next_row_id(state)
    for row in state.rows:
        new_rows.append(row)
        if row.row_id == row_id:
            new_rows.append(row.with_changes(row_id=duplicate_id))
    return replace(state, rows=tuple(new_rows))


def next_row_id(state: CalculatorState) -> str:
    """Return the next numeric row id for this state."""

    numeric_ids = [int(row.row_id) for row in state.rows if row.row_id.isdigit()]
    if numeric_ids:
        return str(max(numeric_ids) + 1)
    return str(len(state.rows) + 1)
