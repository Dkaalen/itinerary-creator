"""Streamlit issue display helpers for export workflow."""

from __future__ import annotations

import streamlit as st


def show_issue_list(title: str, issues) -> None:
    st.error(title)
    with st.expander("Show details"):
        for issue in issues:
            st.write(f"- {getattr(issue, 'message', issue)}")


def show_review_issue_list(title: str, issues) -> None:
    """Show advisory findings without presenting them as export failures."""

    items = tuple(issues or ())
    if not items:
        return
    st.warning(title)
    with st.expander("Show review notes"):
        for issue in items:
            st.write(f"- {getattr(issue, 'message', issue)}")


__all__ = ["show_issue_list", "show_review_issue_list"]
