"""Render the read-only Local Library filters, result table, and record details."""

from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from calculator.library_browser import (
    LocalLibraryBrowserFilters,
    filter_local_library_rows,
    local_library_city,
    local_library_filter_options,
    paginate_local_library_rows,
)
from calculator.library_model import FORMULA_FIELD_NAMES, LocalLibraryRow
from calculator.library_store import LocalLibraryReadResult

_PAGE_SIZE_OPTIONS = (25, 50, 100)
_ALL = "All"


def render_local_library_browser(library_read: LocalLibraryReadResult) -> None:
    """Render a bounded, read-only browser for valid workbook records."""

    if library_read.message:
        st.error(library_read.message)
        return
    if not library_read.rows:
        st.info("The bundled Excel workbook does not contain any valid Local Library records.")
        return

    options = local_library_filter_options(library_read.rows)
    filters = _render_filters(options)
    filtered_rows = filter_local_library_rows(library_read.rows, filters)
    _reset_page_when_filters_change(filters)
    page_size, requested_page = _render_paging_controls(len(filtered_rows))
    page = paginate_local_library_rows(filtered_rows, page_number=requested_page, page_size=page_size)

    st.caption(
        f"Showing {len(page.rows)} of {page.total_rows} matching records · "
        f"Page {page.page_number} of {page.page_count}."
    )
    if not page.rows:
        st.info("No Local Library records match the selected filters.")
        return

    st.dataframe(
        [_summary_row(row) for row in page.rows],
        use_container_width=True,
        hide_index=True,
    )
    rows_by_id = {row.library_id: row for row in page.rows}
    selected_key = "local_library_browser_selected_record"
    selected_id = str(st.session_state.get(selected_key) or "")
    if selected_id not in rows_by_id:
        st.session_state[selected_key] = page.rows[0].library_id
    selected_id = st.selectbox(
        "Record details",
        tuple(rows_by_id),
        format_func=lambda value: _record_label(rows_by_id[value]),
        key=selected_key,
    )
    render_local_library_record_details(rows_by_id[selected_id])


def render_local_library_record_details(row: LocalLibraryRow) -> None:
    """Render every stored field for one Local Library record."""

    st.subheader(row.travel_element or row.supplier or "Local Library record")
    source, content, pricing, formulas, metadata = _detail_groups(row)
    _render_detail_table("Source", source)
    _render_detail_table("Content", content)
    _render_detail_table("Pricing and VAT", pricing)
    _render_detail_table("Workbook formulas", formulas)
    _render_detail_table("Record metadata", metadata)


def _render_filters(options: dict[str, tuple[str, ...]]) -> LocalLibraryBrowserFilters:
    st.subheader("Browse records")
    with st.container(key="local_library_filters"):
        query = st.text_input(
            "Search",
            placeholder="Travel element, supplier, comments, URL, or library ID",
            key="local_library_browser_query",
        )
        first = st.columns(3, gap="small")
        second = st.columns(3, gap="small")
        worksheet = first[0].selectbox("Worksheet", (_ALL, *options["worksheet"]))
        country = first[1].selectbox("Country", (_ALL, *options["country"]))
        city = first[2].selectbox("City", (_ALL, *options["city"]))
        row_type = second[0].selectbox("Type", (_ALL, *options["row_type"]))
        supplier = second[1].selectbox("Supplier", (_ALL, *options["supplier"]))
        currency = second[2].selectbox("Currency", (_ALL, *options["currency"]))
    return LocalLibraryBrowserFilters(
        worksheet=_selected_value(worksheet),
        country=_selected_value(country),
        city=_selected_value(city),
        row_type=_selected_value(row_type),
        supplier=_selected_value(supplier),
        currency=_selected_value(currency),
        query=query,
    )


def _reset_page_when_filters_change(filters: LocalLibraryBrowserFilters) -> None:
    signature_key = "local_library_browser_filter_signature"
    signature = repr(filters)
    if st.session_state.get(signature_key) != signature:
        st.session_state[signature_key] = signature
        st.session_state["local_library_browser_page"] = 1


def _render_paging_controls(total_rows: int) -> tuple[int, int]:
    with st.container(key="local_library_paging"):
        controls = st.columns([0.3, 0.7], gap="small")
        page_size = controls[0].selectbox(
            "Rows per page",
            _PAGE_SIZE_OPTIONS,
            index=1,
            key="local_library_browser_page_size",
        )
        page_count = max(1, (total_rows + int(page_size) - 1) // int(page_size))
        page_key = "local_library_browser_page"
        current_page = min(max(1, int(st.session_state.get(page_key, 1))), page_count)
        st.session_state[page_key] = current_page
        page_number = controls[1].number_input(
            "Page",
            min_value=1,
            max_value=page_count,
            step=1,
            key=page_key,
        )
    return int(page_size), int(page_number)


def _summary_row(row: LocalLibraryRow) -> dict[str, object]:
    return {
        "Worksheet": row.source_sheet,
        "Row": row.source_row,
        "Country": row.country,
        "City": local_library_city(row),
        "Type": row.type,
        "Supplier": row.supplier,
        "Travel element": row.travel_element,
        "Supplier currency": row.supplier_currency,
        "Sales currency": row.sales_currency,
    }


def _record_label(row: LocalLibraryRow) -> str:
    return f"{row.source_sheet} row {row.source_row} · {row.travel_element or row.library_id}"


def _detail_groups(row: LocalLibraryRow) -> tuple[dict[str, object], ...]:
    values = asdict(row)
    source_fields = (
        "source_workbook",
        "source_sheet",
        "source_row",
        "country",
    )
    content_fields = (
        "category",
        "kalk_id",
        "day",
        "type",
        "from_date",
        "to_date",
        "from_time",
        "to_time",
        "supplier",
        "travel_element",
        "manual_booking",
        "status",
        "comments",
        "non_refundable",
        "refundable",
        "url",
    )
    pricing_fields = (
        "gross_price_per_unit",
        "units",
        "gross_price",
        "supplier_commission",
        "net_price",
        "supplier_currency",
        "supplier_x_rate",
        "net_price_nok",
        "sales_price_per_unit",
        "price",
        "sales_currency",
        "sales_x_rate",
        "sales_price_nok_total",
        "gp_nok",
        "gp_percent",
        "vat25",
        "vat15",
        "vat12",
        "vat0_domestic",
        "vat0_international",
    )
    metadata_fields = (
        "schema_version",
        "library_id",
        "record_type",
        "is_fetchable",
        "is_deleted",
        "search_text",
        "created_at",
        "updated_at",
        "updated_by",
    )
    return (
        _pick(values, source_fields),
        _pick(values, content_fields),
        _pick(values, pricing_fields),
        _pick(values, FORMULA_FIELD_NAMES),
        _pick(values, metadata_fields),
    )


def _render_detail_table(title: str, values: dict[str, object]) -> None:
    with st.expander(title, expanded=title in {"Source", "Content"}):
        st.dataframe(
            [{"Field": key, "Value": _display_value(value)} for key, value in values.items()],
            use_container_width=True,
            hide_index=True,
        )


def _pick(values: dict[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    return {field: values.get(field) for field in fields}


def _display_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return value


def _selected_value(value: str) -> str:
    return "" if value == _ALL else value
