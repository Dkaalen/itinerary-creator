"""Debug-only generation review messages for Streamlit workflow pages."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from app_modules.debug_mode import is_debug_mode
from app_modules.validation_gate import render_warning_issues


def render_generation_messages(state: MutableMapping[str, Any]) -> None:
    """Render parser/generation diagnostics only when debug mode is enabled."""

    if not is_debug_mode(state):
        return
    from ui.input_review_panel import render_structured_input_review_panel

    render_structured_input_review_panel(
        state.get("parsed_rows", []),
        state.get("parser_diagnostics", []),
        state.get("structured_input_review"),
    )
    duplicate_count = state.get("generation_duplicate_count", 0)
    if duplicate_count:
        st.warning(f"Skipped approximately {duplicate_count} duplicate, continuation, or malformed row(s).")
    for warning in state.get("generation_overflow_warnings", []) or []:
        st.warning(warning)
    validation_report = state.get("itinerary_validation_report")
    if validation_report:
        render_warning_issues(validation_report)
