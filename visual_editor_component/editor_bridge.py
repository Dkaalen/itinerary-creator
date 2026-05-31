"""Python bridge for the editable A4 visual editor component."""

from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent / "frontend"

_visual_page_editor = components.declare_component(
    "visual_page_editor",
    path=str(_COMPONENT_DIR),
)


def render_visual_page_editor(payload, key="visual_page_editor", commit_nonce=None):
    """Render the custom editable-page component and return saved edits.

    The frontend returns a JSON string when the user clicks "Save now"
    or when Streamlit requests a commit before PDF export. Until then
    editing stays local in the browser and does not trigger reruns.
    """
    return _visual_page_editor(payload=payload, commit_nonce=commit_nonce, key=key, default=None)
