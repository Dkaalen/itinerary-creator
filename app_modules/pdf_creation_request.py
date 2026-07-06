"""Create-PDF request orchestration for the export workflow."""

from __future__ import annotations

import streamlit as st

from app_modules.export_actions import clear_pdf_artifact, create_pdf_from_current_preview
from app_modules.export_identity import export_signature_for_state
from app_modules.export_job_state import mark_export_failed, mark_export_ready, mark_exporting
from app_modules.saved_project_current_state import refresh_active_saved_project_current_snapshot
from app_modules.pdf_editor_commit_gate import (
    clear_pdf_editor_commit,
    pdf_editor_commit_pending as _pdf_editor_commit_pending,
    pdf_transaction_state as _pdf_transaction_state,
    start_pdf_editor_commit,
)


def create_pdf_now() -> bool:
    """Create the PDF immediately from the current committed preview state."""

    mark_exporting(st.session_state, signature=export_signature_for_state(st.session_state))
    ok = False
    try:
        with st.spinner("Creating PDF…"):
            ok = create_pdf_from_current_preview()
    except Exception as error:
        clear_pdf_artifact("PDF failed")
        mark_export_failed(st.session_state, error=str(error))
        st.session_state["export_last_error"] = str(error)
        st.error("PDF export failed in this environment. The editable itinerary preview is still available.")
        with st.expander("PDF export error details"):
            st.exception(error)
        return False
    if ok:
        mark_export_ready(st.session_state, signature=export_signature_for_state(st.session_state))
    else:
        mark_export_failed(st.session_state, error=st.session_state.get("pdf_status") or "PDF export failed.")
    return ok


def clear_stale_pdf_editor_state() -> None:
    """Clear any stale PDF editor-commit transaction before a new request."""

    clear_pdf_editor_commit(st.session_state)


def pdf_transaction_state():
    """Return the current Create PDF workflow transaction."""

    return _pdf_transaction_state(st.session_state)


def pdf_editor_commit_pending() -> bool:
    """Return whether Create PDF is waiting on a visible-editor save."""

    return _pdf_editor_commit_pending(st.session_state)


def queue_synced_pdf_creation() -> None:
    """Ask the browser editor to save, then rerun into automatic PDF creation."""

    start_pdf_editor_commit(st.session_state, auto_create_pdf=True)
    st.rerun()


def request_pdf_creation() -> None:
    """Create the PDF from the latest committed state and refresh saved-project payload."""

    clear_stale_pdf_editor_state()
    if create_pdf_now():
        refresh_active_saved_project_current_snapshot(st.session_state)
        st.success("PDF created. Use the download button.")
        st.rerun()
