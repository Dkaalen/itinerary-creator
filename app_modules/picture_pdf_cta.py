"""Picture-stage Create PDF call-to-action and editor-save transaction UI."""

from __future__ import annotations

import streamlit as st

from app_modules.export_actions import current_pdf_bytes
from app_modules.pdf_editor_commit_gate import (
    clear_pdf_editor_commit,
    pdf_editor_commit_pending,
    pdf_transaction_state,
    retry_pdf_editor_commit,
    start_pdf_editor_commit,
)
from app_modules.workflow_actions import enter_export_stage
from app_modules.workflow_transactions import transaction_timeout_copy, transaction_wait_copy


def enter_export_stage_for_synced_pdf() -> None:
    """Move to export and request automatic PDF creation from committed editor state."""

    enter_export_stage(st.session_state, auto_create_pdf=True)
    st.rerun()


def maybe_continue_ready_pdf_transaction() -> None:
    """Continue a pending picture-stage PDF request once the editor commit is ready."""

    if pdf_transaction_state(st.session_state).ready:
        enter_export_stage_for_synced_pdf()


def render_picture_pdf_cta() -> None:
    """Render the picture-stage PDF CTA without owning page layout."""

    st.html(
        '<div class="bottom-cta"><div><strong>Pictures reviewed?</strong>'
        '<span>Create the final PDF from the current document.</span></div></div>'
    )
    if current_pdf_bytes():
        return

    transaction = pdf_transaction_state(st.session_state)
    if transaction.ready:
        st.success("Image edits applied. Creating the PDF from the current document…")
        enter_export_stage_for_synced_pdf()
        return

    if pdf_editor_commit_pending(st.session_state):
        _render_pending_pdf_commit(transaction)
        return

    if st.button("Create PDF", type="primary", use_container_width=True):
        # Export is a hard sync boundary: image removals, replacements, uploads,
        # and crop focus changes live locally while the user reviews pictures, but
        # the PDF must be created from the exact visible editor state.
        start_pdf_editor_commit(st.session_state)
        st.rerun()


def _render_pending_pdf_commit(transaction) -> None:
    if transaction.timed_out:
        st.warning(transaction_timeout_copy(transaction))
        st.caption("Retry the save, create the PDF from the last saved version, or cancel and keep reviewing pictures.")
        with st.container(key="workflow_transaction_actions_picture_pdf"):
            retry_col, saved_col, cancel_col = st.columns([0.22, 0.56, 0.22], gap="small")
            with retry_col:
                if st.button("Retry save", type="primary", use_container_width=True, key="retry_picture_pdf_editor_commit"):
                    retry_pdf_editor_commit(st.session_state)
                    st.rerun()
            with saved_col:
                if st.button("Create PDF from last saved version", use_container_width=True, key="fallback_picture_pdf_after_timeout"):
                    clear_pdf_editor_commit(st.session_state)
                    enter_export_stage_for_synced_pdf()
            with cancel_col:
                if st.button("Cancel", use_container_width=True, key="cancel_picture_pdf_editor_commit"):
                    clear_pdf_editor_commit(st.session_state)
                    st.rerun()
        return

    st.info(transaction_wait_copy(transaction))
    st.button("Create PDF", disabled=True, use_container_width=True)
    if st.button("Create PDF from last saved version", use_container_width=True):
        clear_pdf_editor_commit(st.session_state)
        enter_export_stage_for_synced_pdf()
