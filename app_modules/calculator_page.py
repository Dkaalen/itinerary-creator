"""Render the in-app itinerary calculator page."""

from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _stage_panel
from app_modules.calculator_backup_action import render_calculator_backup_controls
from app_modules.calculator_download_action import render_calculation_download_button
from app_modules.calculator_editor_sync import calculator_grid_widget_key, store_calculator_state
from app_modules.calculator_generation_action import generate_itinerary_from_calculator
from app_modules.calculator_grid_config import calculator_column_config
from app_modules.calculator_grid_data import rows_to_table_data, table_data_to_rows
from app_modules.calculator_library_cache import read_cached_local_library
from app_modules.calculator_navigation import (
    CALCULATOR_STATE_KEY,
    close_calculator_page,
)
from app_modules.validation_gate import block_generation, render_blocking_issues
from app_modules.workflow_config import CALCULATOR_COPY
from calculator.calculations import calculate_totals
from calculator.calculator_state import (
    CalculatorState,
    add_rows,
    create_initial_calculator_state,
    delete_row,
    duplicate_row,
)
from calculator.fetch_lines import (
    autofill_exact_travel_element_matches,
    fetch_library_line_into_row_preserving_context,
)
from calculator.grid_autocomplete import TravelElementSuggestionGroup, find_travel_element_suggestion_groups
from calculator.library_model import LocalLibraryRow
from calculator.library_search import LocalLibrarySearchResult, library_result_label, library_result_preview
from calculator.library_store import LocalLibraryReadResult
from calculator.row_model import FORMULA_FIELD_KEYS, CalculatorRow

_ADVANCED_TOGGLE_KEY = "calculator_show_advanced"
_ROW_ACTION_KEY = "calculator_selected_row_id"
_GRID_SUGGESTION_KEY = "calculator_grid_travel_element_suggestion"
_DISABLED_COLUMNS = ("row_id", *FORMULA_FIELD_KEYS)


def render_calculator_page(app_version: str) -> None:
    """Render the standalone calculator page."""

    state = _calculator_state_from_session()
    library_read = read_cached_local_library(st.session_state)
    _render_app_header(app_version, stage="input")
    _stage_panel(CALCULATOR_COPY["panel_title"], CALCULATOR_COPY["panel_text"])
    _render_top_actions()

    itinerary_name = st.text_input(
        "Itinerary name",
        value=state.itinerary_name,
        key="calculator_itinerary_name_input",
    )
    state = state.with_itinerary_name(itinerary_name)
    _store_calculator_state(state)

    show_advanced = st.toggle("Show advanced columns", key=_ADVANCED_TOGGLE_KEY)
    draft_rows, saved = _render_grid(state, show_advanced=show_advanced)
    draft_state = CalculatorState(itinerary_name=itinerary_name, rows=tuple(draft_rows))

    filled_state = _render_grid_travel_element_suggestions(draft_state, library_read)
    if filled_state is not None:
        _store_calculator_state(filled_state, refresh_grid=True)
        st.rerun()

    if saved:
        saved_state = autofill_exact_travel_element_matches(draft_state, library_read.rows)
        _store_calculator_state(saved_state, refresh_grid=True)
        st.success("Calculator edits saved.")
        st.rerun()

    _render_row_actions(draft_state)
    _render_totals(draft_state)
    render_calculation_download_button(draft_state)
    _render_generation_actions(draft_state)
    _render_backup_controls(draft_state)


def _calculator_state_from_session() -> CalculatorState:
    state = st.session_state.get(CALCULATOR_STATE_KEY)
    if isinstance(state, CalculatorState):
        return state
    new_state = create_initial_calculator_state()
    _store_calculator_state(new_state)
    return new_state


def _store_calculator_state(state: CalculatorState, *, refresh_grid: bool = False) -> None:
    store_calculator_state(st.session_state, state, refresh_grid=refresh_grid)


def _render_top_actions() -> None:
    left, right = st.columns([1, 3])
    with left:
        if st.button("Back to itinerary creator", use_container_width=True):
            close_calculator_page(st.session_state)
            st.rerun()
    with right:
        st.caption("Type directly in the Travel element cells; matching Local Library lines appear below the grid.")


def _render_grid(state: CalculatorState, *, show_advanced: bool) -> tuple[tuple[CalculatorRow, ...], bool]:
    data = rows_to_table_data(state.rows, show_advanced=show_advanced)
    edited = st.data_editor(
        data,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled=_DISABLED_COLUMNS,
        column_config=calculator_column_config(show_advanced),
        key=calculator_grid_widget_key(st.session_state),
    )
    saved = st.button("Save calculator edits", use_container_width=True)
    return table_data_to_rows(edited, state.rows), saved


def _render_grid_travel_element_suggestions(
    state: CalculatorState,
    read_result: LocalLibraryReadResult,
) -> CalculatorState | None:
    st.caption(_library_read_status(read_result))

    groups = find_travel_element_suggestion_groups(state.rows, read_result.rows)
    if not groups:
        st.caption("Type at least 2 characters in a Travel element cell to see Local Library suggestions.")
        return None

    group = groups[0]
    st.markdown(f"**Local Library suggestions for row {group.row_id}:** `{group.query}`")
    selected_library_id = st.selectbox(
        "Suggestions",
        options=[result.row.library_id for result in group.results],
        format_func=lambda library_id: _library_option_label(group.results, library_id),
        key=f"{_GRID_SUGGESTION_KEY}_{group.row_id}_{group.query}",
    )
    selected_result = _selected_library_result(group.results, str(selected_library_id))
    if selected_result is None:
        return None

    st.caption(_compact_library_preview(selected_result.row))
    if not st.button(f"Fetch selected line into row {group.row_id}", type="primary", use_container_width=True):
        return None
    return fetch_library_line_into_row_preserving_context(state, selected_result.row, group.row_id)


def _render_row_actions(state: CalculatorState) -> str | None:
    add_one_col, add_five_col, add_ten_col, select_col, duplicate_col, delete_col = st.columns([1, 1, 1, 2, 1, 1])
    with add_one_col:
        if st.button("+1 row", use_container_width=True):
            _store_calculator_state(add_rows(state, 1), refresh_grid=True)
            st.rerun()
    with add_five_col:
        if st.button("+5 rows", use_container_width=True):
            _store_calculator_state(add_rows(state, 5), refresh_grid=True)
            st.rerun()
    with add_ten_col:
        if st.button("+10 rows", use_container_width=True):
            _store_calculator_state(add_rows(state, 10), refresh_grid=True)
            st.rerun()

    selected_row_id = _render_row_selector(select_col, state)
    with duplicate_col:
        if st.button("Duplicate row", use_container_width=True, disabled=selected_row_id is None):
            _store_calculator_state(duplicate_row(state, str(selected_row_id)), refresh_grid=True)
            st.rerun()
    with delete_col:
        if st.button("Delete row", use_container_width=True, disabled=selected_row_id is None):
            _store_calculator_state(delete_row(state, str(selected_row_id)), refresh_grid=True)
            st.rerun()
    return selected_row_id


def _render_row_selector(column: object, state: CalculatorState) -> str | None:
    with column:
        if not state.rows:
            st.caption("No rows yet.")
            return None
        return st.selectbox(
            "Row actions",
            options=[row.row_id for row in state.rows],
            format_func=lambda row_id: _row_option_label(state, row_id),
            key=_ROW_ACTION_KEY,
        )


def _render_totals(state: CalculatorState) -> None:
    totals = calculate_totals(state.rows)
    total_col, sales_col, gp_col, gp_percent_col = st.columns(4)
    total_col.metric("Price", _format_money(totals.price))
    sales_col.metric("Sales NOK", _format_money(totals.sales_price_nok_total))
    gp_col.metric("GP NOK", _format_money(totals.gp_nok))
    gp_percent_col.metric("GP %", f"{totals.gp_percent:.1%}")


def _render_generation_actions(state: CalculatorState) -> None:
    agent_col, customer_col = st.columns(2)
    generate_agent = agent_col.button("Generate Agent Itinerary", type="primary", use_container_width=True)
    generate_customer = customer_col.button("Generate Customer Itinerary", use_container_width=True)
    if not (generate_agent or generate_customer):
        return

    output_brand = "booknordics_customer" if generate_customer else "agent"
    with st.spinner("Building your itinerary…"):
        result = generate_itinerary_from_calculator(st.session_state, state, output_brand=output_brand)

    if result.ok:
        st.rerun()
        return

    validation_report = (result.payload or {}).get("validation_report") if result.payload else None
    if validation_report is not None:
        block_generation(validation_report)
        render_blocking_issues(validation_report)
    elif result.message:
        st.warning(result.message)


def _render_backup_controls(state: CalculatorState) -> None:
    imported_state = render_calculator_backup_controls(state)
    if imported_state is None:
        return
    _store_calculator_state(imported_state, refresh_grid=True)
    st.success("Calculator backup reopened.")
    st.rerun()


def _library_read_status(read_result: LocalLibraryReadResult) -> str:
    fetchable_count = sum(1 for row in read_result.rows if row.is_available_for_fetch)
    if read_result.source == "google_sheets" and not read_result.read_only:
        return f"Local Library: Google Sheets connected ({fetchable_count} fetchable lines)."
    message = read_result.message or "Using bundled read-only Local Library fixture."
    return f"Local Library: {message} ({fetchable_count} fallback lines)."


def _selected_library_result(
    results: tuple[LocalLibrarySearchResult, ...],
    library_id: str,
) -> LocalLibrarySearchResult | None:
    return next((result for result in results if result.row.library_id == library_id), None)


def _library_option_label(results: tuple[LocalLibrarySearchResult, ...], library_id: str) -> str:
    selected_result = _selected_library_result(results, str(library_id))
    if selected_result is None:
        return str(library_id)
    return library_result_label(selected_result.row)


def _compact_library_preview(row: LocalLibraryRow) -> str:
    preview = library_result_preview(row).replace("\n", " • ")
    return preview[:450]


def _row_option_label(state: CalculatorState, row_id: str) -> str:
    row = next((item for item in state.rows if item.row_id == row_id), None)
    if row is None:
        return str(row_id)
    label = " · ".join(part for part in (row.day, row.type, row.travel_element) if part)
    return f"{row.row_id}: {label}" if label else f"{row.row_id}: Empty row"


def _format_money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")
