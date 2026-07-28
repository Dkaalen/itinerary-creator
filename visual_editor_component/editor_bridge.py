"""Python bridge for the editable A4 visual editor component."""

from pathlib import Path
import streamlit.components.v1 as components

from app_modules.browser_storage_contract import browser_storage_contract

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
    component_payload = dict(payload or {})
    component_payload["browser_storage_contract"] = browser_storage_contract()
    return _visual_page_editor(payload=component_payload, commit_nonce=commit_nonce, key=key, default=None)
