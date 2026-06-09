"""Streamlit-facing workflow helpers for itinerary structural validation."""

from __future__ import annotations

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - exercised in lightweight test environments
    st = None

from itinerary_generation.quality_gate import ItineraryQualityGateReport, evaluate_itinerary_quality


BLOCKED_STATUS = "Blocked by validation"


def evaluate_rows(parsed_rows) -> ItineraryQualityGateReport:
    """Return the structural quality-gate report for parsed rows."""
    return evaluate_itinerary_quality(parsed_rows)


def block_generation(report: ItineraryQualityGateReport) -> None:
    """Clear generated output state after a blocking structural validation failure."""
    if st is None:
        return
    st.session_state.parsed_rows = []
    st.session_state.output_edits = {}
    st.session_state.itinerary_html = ""
    st.session_state.pdf_bytes = None
    st.session_state.export_pdf_bytes = None
    st.session_state.pdf_signature = None
    st.session_state.export_pdf_signature = None
    st.session_state.preview_signature = None
    st.session_state.html_path = None
    st.session_state.pdf_status = BLOCKED_STATUS
    st.session_state.itinerary_validation_report = report


def render_blocking_issues(report: ItineraryQualityGateReport) -> None:
    if st is None:
        return
    for issue in report.blocking_issues:
        st.error(issue.message)
    if report.is_blocked:
        st.warning(
            "The itinerary was not generated because the parsed structure appears unsafe. "
            "Check optional/add-on rows and try again."
        )


def render_warning_issues(report: ItineraryQualityGateReport) -> None:
    if st is None:
        return
    for issue in report.warnings:
        st.warning(issue.message)


def validate_for_generation(parsed_rows) -> ItineraryQualityGateReport:
    """Evaluate parsed rows without mutating Streamlit or workflow state."""
    return evaluate_rows(parsed_rows)
