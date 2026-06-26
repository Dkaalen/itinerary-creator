"""Legacy PDF editor-commit compatibility helpers.

PDF export no longer waits on a browser-side visual-editor commit.  The export
flow uses the latest server-saved editor state so a missing component
acknowledgement cannot hang the app.  These wrappers remain for older imports
and clear stale commit state instead of creating new pending work.
"""

from __future__ import annotations

import streamlit as st

from app_modules.editor_commit import clear_pdf_editor_commit_request


def request_pdf_creation_after_visual_editor_commit() -> None:
    """Compatibility no-op: PDF creation must not start a blocking commit wait."""

    clear_pdf_editor_commit_request(st.session_state)


def visual_editor_export_commit_ready() -> bool:
    return True


__all__ = ["request_pdf_creation_after_visual_editor_commit", "visual_editor_export_commit_ready"]
