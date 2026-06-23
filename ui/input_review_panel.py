"""Streamlit rendering helpers for structured input review."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from itinerary_generation.input_review import (
    StructuredInputReview,
    apply_input_correction_actions,
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
            "Confidence": f"{row.confidence}% · {row.confidence_label}",
            "Priority": row.review_priority,
            "Status": row.status,
            "Destination": row.destination_status,
            "Next action": row.next_action,
            "Primary fix": row.primary_fix,
            "Missing fields": ", ".join(row.missing_fields),
            "Review flags": ", ".join(row.flags),
        }
        for row in review.row_reviews
    ]


def _correction_action_rows(review: StructuredInputReview) -> list[dict[str, Any]]:
    return [
        {
            "Row": action.row_number,
            "Action": action.action_label,
            "Fields updated": ", ".join(action.field_updates.keys()),
            "Safe": "Yes" if action.safe_auto_apply else "Review",
            "Reason": action.reason,
        }
        for action in review.correction_actions
    ]


def _accept_safe_parser_fixes(rows: list[dict], diagnostics: list[dict], review: StructuredInputReview) -> int:
    corrected_rows, applied = apply_input_correction_actions(rows, review.correction_actions)
    if not applied:
        return 0
    st.session_state["parsed_rows"] = corrected_rows
    st.session_state["structured_input_review"] = build_structured_input_review(
        corrected_rows,
        parser_diagnostics=diagnostics,
    )
    st.session_state["input_corrections_applied"] = [action.as_dict() for action in applied]
    st.session_state["pdf_status"] = "Not created"
    st.session_state["pdf_dirty"] = True
    return len(applied)


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
        if resolved.low_confidence_count:
            st.caption("Correction queue: handle blocker rows first, then review medium-confidence rows before final polishing.")
        st.dataframe(_review_table_rows(resolved), hide_index=True, use_container_width=True)

        if resolved.correction_actions:
            st.caption("Safe parser fixes")
            st.dataframe(_correction_action_rows(resolved), hide_index=True, use_container_width=True)
            if st.button("Accept safe parser fixes", key="accept_safe_input_parser_fixes", use_container_width=True):
                applied_count = _accept_safe_parser_fixes(list(rows), list(diagnostics), resolved)
                if applied_count:
                    st.success(f"Accepted {applied_count} safe parser fix(es). Refresh the itinerary before creating a new PDF.")
                    st.rerun()

        st.caption("Review summary")
        st.code(format_structured_input_review(resolved), language=None)
