"""Streamlit control for controlled itinerary tone presets."""

from __future__ import annotations

import streamlit as st

from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET, TONE_PRESETS, normalize_tone_preset

TONE_PRESET_STATE_KEY = "tone_preset"


def render_tone_preset_selector() -> str:
    """Render and return the selected tone preset id."""

    current = normalize_tone_preset(st.session_state.get(TONE_PRESET_STATE_KEY, DEFAULT_TONE_PRESET))
    options = list(TONE_PRESETS)
    selected = st.selectbox(
        "Tone preset",
        options,
        index=options.index(current) if current in options else options.index(DEFAULT_TONE_PRESET),
        format_func=lambda preset_id: TONE_PRESETS[preset_id].label,
        key=TONE_PRESET_STATE_KEY,
    )
    return normalize_tone_preset(selected)


__all__ = ["TONE_PRESET_STATE_KEY", "render_tone_preset_selector"]
