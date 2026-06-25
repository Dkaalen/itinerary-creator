"""Visual-editor commit coordination for PDF export."""

from __future__ import annotations

import streamlit as st

from app_modules.editor_commit import pdf_editor_commit_ready, request_pdf_editor_commit


def request_pdf_creation_after_visual_editor_commit() -> None:
    """Ask the visual editor to save before PDF creation starts."""

    request_pdf_editor_commit(st.session_state)


def visual_editor_export_commit_ready() -> bool:
    return pdf_editor_commit_ready(st.session_state)


__all__ = ["request_pdf_creation_after_visual_editor_commit", "visual_editor_export_commit_ready"]
