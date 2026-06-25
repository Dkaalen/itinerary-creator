from __future__ import annotations

import streamlit as st

from app_modules.debug_mode import is_debug_mode


def render_debug_tools() -> None:
    if not is_debug_mode(st.session_state):
        return
    from ui.diagnostics_panel import render_itinerary_health_report_panel, render_parser_diagnostics_panel

    with st.container(border=True):
        render_parser_diagnostics_panel()
        render_itinerary_health_report_panel(
            st.session_state.get("parsed_rows", []),
            st.session_state.get("itinerary_validation_report"),
        )
        if st.session_state.get("parsed_rows"):
            st.dataframe(st.session_state.parsed_rows, use_container_width=True)
