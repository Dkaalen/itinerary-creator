"""Streamlit rendering helpers for structured input review."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from itinerary_generation.input_review import StructuredInputReview, build_structured_input_review, format_structured_input_review


def _coerce_review(value: Any, rows: list[dict], parser_diagnostics: list[dict]) -> StructuredInputReview:
    if isinstance(value, StructuredInputReview):
        return value
    return build_structured_input_review(rows, parser_diagnostics=parser_diagnostics)


def render_structured_input_review_panel(
    parsed_rows: list[dict] | None = None,
    parser_diagnostics: list[dict] | None = None,
    review: StructuredInputReview | Mapping[str, Any] | None = None,
) -> None:
    rows = parsed_rows if parsed_rows is not None else st.session_state.get("parsed_rows", [])
    diagnostics = parser_diagnostics if parser_diagnostics is not None else st.session_state.get("parser_diagnostics", [])
    if not rows:
        return
    resolved = _coerce_review(review or st.session_state.get("structured_input_review"), rows, diagnostics)
    with st.expander(f"Structured input review — {resolved.status_label}", expanded=resolved.critical_issue_count > 0):
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Rows", resolved.row_count)
        col_b.metric("Days", resolved.day_count)
        col_c.metric("Route", resolved.route_text)
        col_d.metric("Issues", f"{resolved.critical_issue_count}/{resolved.review_issue_count}")
        st.code(format_structured_input_review(resolved), language=None)
