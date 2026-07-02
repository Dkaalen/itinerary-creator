"""Render the Local Library management page."""

from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _stage_panel
from app_modules.calculator_library_cache import clear_cached_local_library, read_cached_local_library
from app_modules.calculator_navigation import open_calculator_page
from calculator.library_editor import (
    display_label_for_local_library_row,
    mark_local_library_row_deleted,
    new_local_library_row,
    update_local_library_row,
)
from calculator.library_model import LocalLibraryRow
from calculator.library_read_summary import summarize_local_library_read
from calculator.library_store import LocalLibraryReadResult, LocalLibraryStore

_SELECTED_LIBRARY_ROW_KEY = "local_library_selected_row_id"
_NEW_ROW_VALUE = "__new_local_library_row__"


def render_local_library_page(app_version: str) -> None:
    """Render Local Library browse/add/edit/remove controls."""

    _render_app_header(app_version, stage="input")
    _stage_panel(
        "Local Library",
        "Add, edit, or remove reusable calculator rows. Google Sheets saves changes; bundled fallback is read-only.",
    )
    _render_top_actions()

    library_read = read_cached_local_library(st.session_state, force_refresh=st.button("Refresh Local Library"))
    _render_source_status(library_read)

    selected_row = _render_row_selector(library_read)
    _render_editor(selected_row, library_read)


def _render_top_actions() -> None:
    if st.button("Back to itinerary calculator", use_container_width=True):
        open_calculator_page(st.session_state)
        st.rerun()


def _render_source_status(library_read: LocalLibraryReadResult) -> None:
    summary = summarize_local_library_read(library_read)
    if summary.level == "success":
        st.success(summary.headline)
    else:
        st.warning(summary.headline)
    st.caption(summary.detail)
    if library_read.read_only:
        st.info(
            "Editing is disabled because the app is using the bundled fallback. "
            "Add Streamlit Cloud Google Sheets secrets to enable persistent add/edit/remove."
        )


def _render_row_selector(library_read: LocalLibraryReadResult) -> LocalLibraryRow:
    active_rows = tuple(row for row in library_read.rows if not row.is_deleted)
    rows_by_id = {row.library_id: row for row in active_rows if row.library_id}
    options = (_NEW_ROW_VALUE, *rows_by_id)
    selected_id = str(st.session_state.get(_SELECTED_LIBRARY_ROW_KEY) or _NEW_ROW_VALUE)
    if selected_id not in options:
        selected_id = _NEW_ROW_VALUE
    selected = st.selectbox(
        "Library row",
        options,
        index=options.index(selected_id),
        format_func=lambda value: "New Local Library row" if value == _NEW_ROW_VALUE else display_label_for_local_library_row(rows_by_id[value]),
    )
    st.session_state[_SELECTED_LIBRARY_ROW_KEY] = selected
    if selected == _NEW_ROW_VALUE:
        return new_local_library_row()
    return rows_by_id[selected]


def _render_editor(row: LocalLibraryRow, library_read: LocalLibraryReadResult) -> None:
    read_only = library_read.read_only
    store = LocalLibraryStore()
    is_existing = row.library_id and row.library_id != _NEW_ROW_VALUE and any(
        item.library_id == row.library_id for item in library_read.rows
    )

    with st.form("local_library_editor_form"):
        st.subheader("Row details")
        left, right = st.columns(2)
        with left:
            country = st.text_input("Country", value=row.country, disabled=read_only)
            category = st.text_input("Category", value=row.category, disabled=read_only)
            row_type = st.text_input("Type", value=row.type, disabled=read_only)
            supplier = st.text_input("Supplier", value=row.supplier, disabled=read_only)
            travel_element = st.text_area("Travel element", value=row.travel_element, disabled=read_only)
            url = st.text_input("URL", value=row.url, disabled=read_only)
        with right:
            is_fetchable = st.checkbox("Fetchable in calculator", value=row.is_fetchable, disabled=read_only)
            manual_booking = st.checkbox("Manual booking?", value=row.manual_booking, disabled=read_only)
            status = st.text_input("Status", value=row.status, disabled=read_only)
            comments = st.text_area("Comments", value=row.comments, disabled=read_only)
            non_refundable = st.checkbox("Non-refundable", value=row.non_refundable, disabled=read_only)
            refundable = st.checkbox("Refundable", value=row.refundable, disabled=read_only)

        st.subheader("Timing")
        time_cols = st.columns(5)
        with time_cols[0]:
            day = st.text_input("Day", value=row.day, disabled=read_only)
        with time_cols[1]:
            from_date = st.text_input("From date", value=row.from_date, disabled=read_only)
        with time_cols[2]:
            to_date = st.text_input("To date", value=row.to_date, disabled=read_only)
        with time_cols[3]:
            from_time = st.text_input("From time", value=row.from_time, disabled=read_only)
        with time_cols[4]:
            to_time = st.text_input("To time", value=row.to_time, disabled=read_only)

        st.subheader("Pricing")
        price_cols = st.columns(5)
        with price_cols[0]:
            gross_price_per_unit = st.number_input(
                "Gross P per unit", value=float(row.gross_price_per_unit), disabled=read_only
            )
        with price_cols[1]:
            units = st.number_input("Units", value=float(row.units), disabled=read_only)
        with price_cols[2]:
            supplier_commission = st.number_input(
                "Supp Comm %", value=float(row.supplier_commission) * 100, disabled=read_only
            )
        with price_cols[3]:
            supplier_currency = st.text_input("Supp curr", value=row.supplier_currency, disabled=read_only)
        with price_cols[4]:
            sales_currency = st.text_input("Sales curr", value=row.sales_currency, disabled=read_only)

        sales_price_per_unit = st.number_input(
            "Sales P per unit", value=float(row.sales_price_per_unit or 0.0), disabled=read_only
        )

        st.subheader("VAT")
        vat_cols = st.columns(5)
        with vat_cols[0]:
            vat25 = st.number_input("VAT25", value=float(row.vat25), disabled=read_only)
        with vat_cols[1]:
            vat15 = st.number_input("VAT15", value=float(row.vat15), disabled=read_only)
        with vat_cols[2]:
            vat12 = st.number_input("VAT12", value=float(row.vat12), disabled=read_only)
        with vat_cols[3]:
            vat0_domestic = st.number_input("VAT0-D", value=float(row.vat0_domestic), disabled=read_only)
        with vat_cols[4]:
            vat0_international = st.number_input("VAT0-I", value=float(row.vat0_international), disabled=read_only)

        save, delete = st.columns(2)
        save_clicked = save.form_submit_button("Save Local Library row", disabled=read_only)
        delete_clicked = delete.form_submit_button(
            "Remove Local Library row", disabled=read_only or not is_existing, type="secondary"
        )

    if save_clicked:
        updated = update_local_library_row(
            row,
            {
                "country": country,
                "category": category,
                "day": day,
                "type": row_type,
                "from_date": from_date,
                "to_date": to_date,
                "from_time": from_time,
                "to_time": to_time,
                "supplier": supplier,
                "travel_element": travel_element,
                "manual_booking": manual_booking,
                "status": status,
                "comments": comments,
                "non_refundable": non_refundable,
                "refundable": refundable,
                "url": url,
                "gross_price_per_unit": gross_price_per_unit,
                "units": units,
                "supplier_commission": supplier_commission,
                "supplier_currency": supplier_currency,
                "sales_price_per_unit": sales_price_per_unit,
                "sales_currency": sales_currency,
                "vat25": vat25,
                "vat15": vat15,
                "vat12": vat12,
                "vat0_domestic": vat0_domestic,
                "vat0_international": vat0_international,
                "is_fetchable": is_fetchable,
            },
        )
        _handle_write_result(store.save_row(updated), updated.library_id)

    if delete_clicked:
        deleted = mark_local_library_row_deleted(row)
        _handle_write_result(store.save_row(deleted), _NEW_ROW_VALUE, success_message="Local Library row removed.")


def _handle_write_result(result: object, selected_id: str, *, success_message: str | None = None) -> None:
    if getattr(result, "ok", False):
        clear_cached_local_library(st.session_state)
        st.session_state[_SELECTED_LIBRARY_ROW_KEY] = selected_id
        st.success(success_message or getattr(result, "message", "Saved Local Library row."))
        st.rerun()
    else:
        st.error(getattr(result, "message", "Could not save Local Library row."))
