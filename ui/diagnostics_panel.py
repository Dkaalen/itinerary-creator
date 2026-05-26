"""Diagnostics panels for the Streamlit itinerary app."""

import streamlit as st


def render_parser_diagnostics_panel():
    warnings = st.session_state.get("parser_diagnostics", [])
    if not warnings:
        return

    with st.expander(f"Parser diagnostics ({len(warnings)} notice(s))", expanded=False):
        st.caption(
            "These are things the parser could not fully understand. "
            "If something looks wrong in the output, the cause may be listed here."
        )
        for entry in warnings:
            st.markdown(f"**{entry['category']}** — {entry['message']}")
            if entry.get("raw"):
                st.code(entry["raw"], language=None)

        diagnostics_text = []
        for entry in warnings:
            diagnostics_text.append(f"[{entry['category']}] {entry['message']}")
            if entry.get("raw"):
                diagnostics_text.append(f"  Raw: {entry['raw']}")
        with st.expander("Show diagnostics text for copying"):
            st.code("\n".join(diagnostics_text), language=None)
