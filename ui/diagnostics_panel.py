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



def render_itinerary_health_report_panel(parsed_rows=None, validation_report=None):
    """Render the copy-friendly diagnostic itinerary health report."""

    from itinerary_generation.health_report import (
        build_itinerary_health_report,
        format_itinerary_health_report,
    )

    rows = parsed_rows if parsed_rows is not None else st.session_state.get("parsed_rows", [])
    if not rows:
        return

    report = build_itinerary_health_report(
        rows,
        validation_report=validation_report or st.session_state.get("itinerary_validation_report"),
        parser_diagnostics=st.session_state.get("parser_diagnostics", []),
    )

    with st.expander("Itinerary Health Report", expanded=False):
        st.caption(
            "Diagnostic summary only. Use this to verify row classification, day coverage, "
            "route coverage, and validation warnings before exporting."
        )

        metric_a, metric_b, metric_c, metric_d = st.columns(4)
        metric_a.metric("Input days", report.input_days)
        metric_b.metric("Generated days", report.generated_days)
        metric_c.metric("Status", report.status)
        metric_d.metric("Health checks", f"{report.critical_issue_count}/{report.review_issue_count}")

        st.code(format_itinerary_health_report(report), language=None)
