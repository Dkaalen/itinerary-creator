from __future__ import annotations

from calculator.calculator_state import (
    add_row,
    create_calculator_state,
    delete_row,
    duplicate_row,
    next_row_id,
    update_row,
)
from calculator.row_model import CalculatorRow


def test_create_calculator_state_keeps_itinerary_name() -> None:
    state = create_calculator_state("Tromso Northern Lights 2026")

    assert state.itinerary_name == "Tromso Northern Lights 2026"
    assert state.rows == ()


def test_add_row_assigns_next_row_id_without_mutating_original_state() -> None:
    state = create_calculator_state("Trip")
    updated = add_row(state, CalculatorRow(day="Day 1", travel_element="Airport transfer"))

    assert state.rows == ()
    assert len(updated.rows) == 1
    assert updated.rows[0].row_id == "1"
    assert updated.rows[0].travel_element == "Airport transfer"
    assert next_row_id(updated) == "2"


def test_add_row_preserves_existing_row_id() -> None:
    state = add_row(create_calculator_state(), CalculatorRow(row_id="LIB-123"))

    assert state.rows[0].row_id == "LIB-123"
    assert next_row_id(state) == "2"


def test_update_row_changes_only_selected_row() -> None:
    state = create_calculator_state()
    state = add_row(state, CalculatorRow(travel_element="Old"))
    state = add_row(state, CalculatorRow(travel_element="Keep"))

    updated = update_row(state, "1", travel_element="New", units=2)

    assert updated.rows[0].travel_element == "New"
    assert updated.rows[0].units == 2
    assert updated.rows[1].travel_element == "Keep"


def test_delete_row_removes_selected_row() -> None:
    state = create_calculator_state()
    state = add_row(state, CalculatorRow(travel_element="Remove"))
    state = add_row(state, CalculatorRow(travel_element="Keep"))

    updated = delete_row(state, "1")

    assert [row.travel_element for row in updated.rows] == ["Keep"]


def test_duplicate_row_inserts_copy_after_source_with_new_id() -> None:
    state = create_calculator_state()
    state = add_row(state, CalculatorRow(travel_element="Copy me", units=2))
    state = add_row(state, CalculatorRow(travel_element="After"))

    updated = duplicate_row(state, "1")

    assert [row.row_id for row in updated.rows] == ["1", "3", "2"]
    assert [row.travel_element for row in updated.rows] == ["Copy me", "Copy me", "After"]
    assert updated.rows[1].units == 2
