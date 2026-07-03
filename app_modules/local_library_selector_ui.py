"""Render the Local Library row selector."""

from __future__ import annotations

import streamlit as st

from app_modules.local_library_state import NEW_LIBRARY_ROW_VALUE, SELECTED_LIBRARY_ROW_KEY
from calculator.library_editor import display_label_for_local_library_row, new_local_library_row
from calculator.library_model import LocalLibraryRow
from calculator.library_store import LocalLibraryReadResult


def render_local_library_row_selector(library_read: LocalLibraryReadResult) -> LocalLibraryRow:
    """Return the selected active Local Library row or a new blank row."""

    active_rows = tuple(row for row in library_read.rows if not row.is_deleted)
    rows_by_id = {row.library_id: row for row in active_rows if row.library_id}
    options = (NEW_LIBRARY_ROW_VALUE, *rows_by_id)
    selected_id = str(st.session_state.get(SELECTED_LIBRARY_ROW_KEY) or NEW_LIBRARY_ROW_VALUE)
    if selected_id not in options:
        selected_id = NEW_LIBRARY_ROW_VALUE
    selected = st.selectbox(
        "Library row",
        options,
        index=options.index(selected_id),
        format_func=lambda value: _format_option(value, rows_by_id),
    )
    st.session_state[SELECTED_LIBRARY_ROW_KEY] = selected
    if selected == NEW_LIBRARY_ROW_VALUE:
        return new_local_library_row()
    return rows_by_id[selected]


def _format_option(value: str, rows_by_id: dict[str, LocalLibraryRow]) -> str:
    if value == NEW_LIBRARY_ROW_VALUE:
        return "New Local Library row"
    return display_label_for_local_library_row(rows_by_id[value])
