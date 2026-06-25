"""Streamlit issue display helpers for export workflow."""

from __future__ import annotations

import streamlit as st


def show_issue_list(title: str, issues) -> None:
    st.error(title)
    with st.expander("Show details"):
        for issue in issues:
            st.write(f"- {getattr(issue, 'message', issue)}")


__all__ = ["show_issue_list"]
