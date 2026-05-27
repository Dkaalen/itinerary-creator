import streamlit as st

from ui.app_constants import COLOR_PRESETS


def get_color_preset_name(output_edits=None):
    name = (output_edits or {}).get("color_preset") or st.session_state.get("color_preset", "Classic Agent")
    if name not in COLOR_PRESETS:
        return "Classic Agent"
    return name


def get_color_preset(output_edits=None):
    return COLOR_PRESETS[get_color_preset_name(output_edits)]


def get_detail_level_name(output_edits=None):
    """Return a safe client-facing detail level for the current state.

    This helper is intentionally defensive because the app can be rebuilt from
    session state, loaded project JSON, or freshly generated edits. A missing
    detail level should never break itinerary rendering.
    """
    return "Rich descriptive"
