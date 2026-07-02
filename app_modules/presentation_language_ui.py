"""Streamlit control for presentation language selection."""

from __future__ import annotations

import streamlit as st

from app_modules.presentation_language import (
    DEFAULT_PRESENTATION_LANGUAGE,
    SUPPORTED_PRESENTATION_LANGUAGES,
    normalize_presentation_language,
)

PRESENTATION_LANGUAGE_STATE_KEY = "presentation_language"


def render_presentation_language_selector() -> str:
    """Render and return the selected presentation language code."""

    current = normalize_presentation_language(st.session_state.get(PRESENTATION_LANGUAGE_STATE_KEY))
    codes = list(SUPPORTED_PRESENTATION_LANGUAGES)
    index = codes.index(current) if current in codes else codes.index(DEFAULT_PRESENTATION_LANGUAGE)
    selected = st.selectbox(
        "Presentation language",
        codes,
        index=index,
        format_func=lambda code: SUPPORTED_PRESENTATION_LANGUAGES.get(code, code),
        key=PRESENTATION_LANGUAGE_STATE_KEY,
    )
    return normalize_presentation_language(selected)


__all__ = ["PRESENTATION_LANGUAGE_STATE_KEY", "render_presentation_language_selector"]
