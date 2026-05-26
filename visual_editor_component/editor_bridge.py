"""Python bridge for the editable A4 visual editor component."""

from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent / "frontend"

_visual_page_editor = components.declare_component(
    "visual_page_editor",
    path=str(_COMPONENT_DIR),
)


def render_visual_page_editor(payload, key="visual_page_editor"):
    """Render the custom editable-page component and return saved edits.

    The frontend returns a JSON string only when the user clicks
    "Save edits to preview/PDF". Until then Streamlit receives None.
    """
    return _visual_page_editor(payload=payload, key=key, default=None)
