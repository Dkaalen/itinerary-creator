"""Streamlit column configuration for the calculator grid."""

from __future__ import annotations

from typing import Any

import streamlit as st


def calculator_column_config(show_advanced: bool) -> dict[str, Any]:
    """Return Streamlit column config for the calculator grid."""

    config: dict[str, Any] = {
        "row_id": st.column_config.TextColumn("ID", disabled=True),
        "day": st.column_config.TextColumn("Day"),
        "type": st.column_config.TextColumn("Type"),
        "from_date": st.column_config.TextColumn("From date"),
        "to_date": st.column_config.TextColumn("To date"),
        "travel_element": st.column_config.TextColumn("Travel element", width="large"),
        "url": st.column_config.LinkColumn("URL"),
        "gross_price_per_unit": st.column_config.NumberColumn("Gross P per unit", format="%.2f"),
        "units": st.column_config.NumberColumn("Units", format="%.2f"),
        "supplier_commission": st.column_config.NumberColumn("Supp Comm", format="%.4f"),
        "supplier_currency": st.column_config.TextColumn("Supp curr"),
        "sales_price_per_unit": st.column_config.NumberColumn("Sales P per unit", format="%.2f"),
        "sales_currency": st.column_config.TextColumn("Sales curr"),
        "gross_price": st.column_config.NumberColumn("Gross P", disabled=True, format="%.2f"),
        "net_price": st.column_config.NumberColumn("Net P", disabled=True, format="%.2f"),
        "supplier_x_rate": st.column_config.NumberColumn("Supp X-rate", disabled=True, format="%.4f"),
        "net_price_nok": st.column_config.NumberColumn("Net P NOK", disabled=True, format="%.2f"),
        "calculated_sales_price_per_unit": st.column_config.NumberColumn("Calc sales/unit", disabled=True, format="%.2f"),
        "price": st.column_config.NumberColumn("Price", disabled=True, format="%.2f"),
        "sales_x_rate": st.column_config.NumberColumn("Sales X-rate", disabled=True, format="%.4f"),
        "sales_price_nok_total": st.column_config.NumberColumn("Sales P NOK tot", disabled=True, format="%.2f"),
        "gp_nok": st.column_config.NumberColumn("GP NOK", disabled=True, format="%.2f"),
        "gp_percent": st.column_config.NumberColumn("GP %", disabled=True, format="%.2%"),
    }
    if show_advanced:
        config.update(_advanced_column_config())
    return config


def _advanced_column_config() -> dict[str, Any]:
    return {
        "from_time": st.column_config.TextColumn("From time"),
        "to_time": st.column_config.TextColumn("To time"),
        "supplier": st.column_config.TextColumn("Supplier"),
        "manual_booking": st.column_config.CheckboxColumn("Manual booking?"),
        "status": st.column_config.TextColumn("Status"),
        "comments": st.column_config.TextColumn("Comments", width="large"),
        "non_refundable": st.column_config.CheckboxColumn("Non-refundable"),
        "refundable": st.column_config.CheckboxColumn("Refundable"),
        "vat25": st.column_config.NumberColumn("VAT25", format="%.2f"),
        "vat15": st.column_config.NumberColumn("VAT15", format="%.2f"),
        "vat12": st.column_config.NumberColumn("VAT12", format="%.2f"),
        "vat0_domestic": st.column_config.NumberColumn("VAT0-D", format="%.2f"),
        "vat0_international": st.column_config.NumberColumn("VAT0-I", format="%.2f"),
    }
