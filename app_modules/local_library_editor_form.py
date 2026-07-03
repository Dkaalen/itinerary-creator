"""Render the Local Library row editor form."""

from __future__ import annotations

import streamlit as st

from app_modules.local_library_state import NEW_LIBRARY_ROW_VALUE
from app_modules.local_library_write_action import handle_local_library_write_result
from calculator.library_editor import mark_local_library_row_deleted, update_local_library_row
from calculator.library_model import LocalLibraryRow
from calculator.library_store import LocalLibraryReadResult, LocalLibraryStore


def render_local_library_editor(row: LocalLibraryRow, library_read: LocalLibraryReadResult) -> None:
    """Render editable controls for one Local Library row."""

    read_only = library_read.read_only
    store = LocalLibraryStore()
    is_existing = row.library_id and row.library_id != NEW_LIBRARY_ROW_VALUE and any(
        item.library_id == row.library_id for item in library_read.rows
    )

    with st.form("local_library_editor_form"):
        values = _render_row_fields(row, read_only=read_only)
        save, delete = st.columns(2)
        save_clicked = save.form_submit_button("Save Local Library row", disabled=read_only)
        delete_clicked = delete.form_submit_button(
            "Remove Local Library row", disabled=read_only or not is_existing, type="secondary"
        )

    if save_clicked:
        updated = update_local_library_row(row, values)
        handle_local_library_write_result(store.save_row(updated), updated.library_id)

    if delete_clicked:
        deleted = mark_local_library_row_deleted(row)
        handle_local_library_write_result(store.save_row(deleted), NEW_LIBRARY_ROW_VALUE, success_message="Local Library row removed.")


def _render_row_fields(row: LocalLibraryRow, *, read_only: bool) -> dict[str, object]:
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
    time_values = _render_timing_fields(row, read_only=read_only)
    st.subheader("Pricing")
    pricing_values = _render_pricing_fields(row, read_only=read_only)
    st.subheader("VAT")
    vat_values = _render_vat_fields(row, read_only=read_only)

    return {
        "country": country,
        "category": category,
        "type": row_type,
        "supplier": supplier,
        "travel_element": travel_element,
        "manual_booking": manual_booking,
        "status": status,
        "comments": comments,
        "non_refundable": non_refundable,
        "refundable": refundable,
        "url": url,
        "is_fetchable": is_fetchable,
        **time_values,
        **pricing_values,
        **vat_values,
    }


def _render_timing_fields(row: LocalLibraryRow, *, read_only: bool) -> dict[str, object]:
    columns = st.columns(5)
    with columns[0]:
        day = st.text_input("Day", value=row.day, disabled=read_only)
    with columns[1]:
        from_date = st.text_input("From date", value=row.from_date, disabled=read_only)
    with columns[2]:
        to_date = st.text_input("To date", value=row.to_date, disabled=read_only)
    with columns[3]:
        from_time = st.text_input("From time", value=row.from_time, disabled=read_only)
    with columns[4]:
        to_time = st.text_input("To time", value=row.to_time, disabled=read_only)
    return {"day": day, "from_date": from_date, "to_date": to_date, "from_time": from_time, "to_time": to_time}


def _render_pricing_fields(row: LocalLibraryRow, *, read_only: bool) -> dict[str, object]:
    columns = st.columns(5)
    with columns[0]:
        gross_price_per_unit = st.number_input("Gross P per unit", value=float(row.gross_price_per_unit), disabled=read_only)
    with columns[1]:
        units = st.number_input("Units", value=float(row.units), disabled=read_only)
    with columns[2]:
        supplier_commission = st.number_input("Supp Comm %", value=float(row.supplier_commission) * 100, disabled=read_only)
    with columns[3]:
        supplier_currency = st.text_input("Supp curr", value=row.supplier_currency, disabled=read_only)
    with columns[4]:
        sales_currency = st.text_input("Sales curr", value=row.sales_currency, disabled=read_only)
    sales_price_per_unit = st.number_input(
        "Sales P per unit", value=float(row.sales_price_per_unit or 0.0), disabled=read_only
    )
    return {
        "gross_price_per_unit": gross_price_per_unit,
        "units": units,
        "supplier_commission": supplier_commission,
        "supplier_currency": supplier_currency,
        "sales_price_per_unit": sales_price_per_unit,
        "sales_currency": sales_currency,
    }


def _render_vat_fields(row: LocalLibraryRow, *, read_only: bool) -> dict[str, object]:
    columns = st.columns(5)
    with columns[0]:
        vat25 = st.number_input("VAT25", value=float(row.vat25), disabled=read_only)
    with columns[1]:
        vat15 = st.number_input("VAT15", value=float(row.vat15), disabled=read_only)
    with columns[2]:
        vat12 = st.number_input("VAT12", value=float(row.vat12), disabled=read_only)
    with columns[3]:
        vat0_domestic = st.number_input("VAT0-D", value=float(row.vat0_domestic), disabled=read_only)
    with columns[4]:
        vat0_international = st.number_input("VAT0-I", value=float(row.vat0_international), disabled=read_only)
    return {
        "vat25": vat25,
        "vat15": vat15,
        "vat12": vat12,
        "vat0_domestic": vat0_domestic,
        "vat0_international": vat0_international,
    }
