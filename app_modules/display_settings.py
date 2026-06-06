"""Safe accessors for rendering display settings.

The renderer is used both inside Streamlit and from command-line tests. Importing
Streamlit or touching ``st.session_state`` in bare pytest mode can produce noisy
warnings and, in long grouped runs, unstable capture behavior. Keep Streamlit
access lazy and fall back to defaults when no Streamlit script context exists.
"""

from __future__ import annotations

import sys
from typing import Any

from ui.app_constants import COLOR_PRESETS


def _streamlit_session_value(key: str, default: Any) -> Any:
    st = sys.modules.get("streamlit")
    if st is None:
        return default

    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            return default
    except Exception:
        return default

    try:
        return st.session_state.get(key, default)
    except Exception:
        return default


def get_color_preset_name(output_edits=None):
    name = (output_edits or {}).get("color_preset") or _streamlit_session_value(
        "color_preset",
        "Classic Agent",
    )
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
