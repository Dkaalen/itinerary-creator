"""Streamlit rendering helpers for structured input review."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from itinerary_generation.input_review import (
    StructuredInputReview,
    build_structured_input_review,
    format_structured_input_review,
)


def _coerce_review(value: Any, rows: list[dict], parser_diagnostics: list[dict]) -> StructuredInputReview:
    if isinstance(value, StructuredInputReview):
        return value
    return build_structured_input_review(rows, parser_diagnostics=parser_diagnostics)


def _review_table_rows(review: StructuredInputReview) -> list[dict[str, Any]]:
    return [
        {
            "Row": row.row_number,
            "Day": row.day,
            "Type": row.service_type,
            "City / route": row.city,
            "Title": row.title,
            "Confidence": f"{row.confidence}%",
            "Status": row.status,
            "Review flags": ", ".join(row.flags),
            "Suggested fixes": "; ".join(row.suggested_fixes),
        }
        for row in review.row_reviews
    ]


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
    expanded = resolved.critical_issue_count > 0 or resolved.low_confidence_count > 0
    with st.expander(f"Structured input review — {resolved.status_label}", expanded=expanded):
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Rows", resolved.row_count)
        col_b.metric("Days", resolved.day_count)
        col_c.metric("Parser confidence", f"{resolved.average_confidence}%")
        col_d.metric("Rows to review", resolved.low_confidence_count)

        st.caption(f"Route: {resolved.route_text}")
        st.dataframe(_review_table_rows(resolved), hide_index=True, use_container_width=True)

        with st.expander("Review summary", expanded=False):
            st.code(format_structured_input_review(resolved), language=None)
