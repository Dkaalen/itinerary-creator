from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _render_stage_actions, _stage_panel
from app_modules.workflow_transactions import (
    WorkflowTransactionTarget,
    clear_workflow_transaction,
    retry_workflow_transaction,
    start_workflow_transaction,
    transaction_timeout_copy,
    transaction_wait_copy,
    workflow_transaction_state,
)
from app_modules.export_actions import current_pdf_bytes
from app_modules.export_step import render_pdf_download_station
from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.image_gateway_ui import (
    _current_image_bank_status,
    _image_status_notice,
    _render_image_bank_gateway_repair,
)
from app_modules.preview_step import _render_document_editor
from app_modules.workflow_actions import enter_export_stage
from app_modules.workflow_config import STAGE_COPY


def _pdf_transaction():
    return workflow_transaction_state(st.session_state, WorkflowTransactionTarget.CREATE_PDF)

def _pdf_commit_pending() -> bool:
    transaction = _pdf_transaction()
    return transaction.pending or transaction.timed_out


def _start_synced_pdf_export() -> None:
    enter_export_stage(st.session_state, auto_create_pdf=True)
    st.rerun()


def render_picture_page(app_version: str) -> None:
    _render_app_header(app_version, stage="pictures")
    _render_stage_actions("pictures")
    render_pdf_download_station(location="top")
    status = _current_image_bank_status()
    if not image_bank_is_ready_for_client_pictures(status):
        st.session_state["image_bank_gateway"] = {
            "ready": False,
            "status": status,
            "message": status.get("blocking_message", ""),
        }
        _render_image_bank_gateway_repair(st.session_state.get("image_bank_gateway"))
        return
    _image_status_notice()
    _stage_panel(STAGE_COPY["pictures"]["panel_title"], STAGE_COPY["pictures"]["panel_text"])

    waiting_for_pdf_commit = _pdf_commit_pending()
    _render_document_editor(pictures_active=True)
    if waiting_for_pdf_commit and _pdf_transaction().ready:
        _start_synced_pdf_export()

    st.html('<div class="bottom-cta"><div><strong>Pictures reviewed?</strong><span>Create the final PDF from the current document.</span></div></div>')
    if current_pdf_bytes():
        return

    if _pdf_transaction().ready:
        st.success("Image edits applied. Creating the PDF from the current document…")
        _start_synced_pdf_export()
        return

    if _pdf_commit_pending():
        transaction = _pdf_transaction()
        if transaction.timed_out:
            st.warning(transaction_timeout_copy(transaction))
            st.caption("Retry the save, create the PDF from the last saved version, or cancel and keep reviewing pictures.")
            retry_col, saved_col, cancel_col = st.columns(3)
            with retry_col:
                if st.button("Retry save", type="primary", use_container_width=True, key="retry_picture_pdf_editor_commit"):
                    retry_workflow_transaction(st.session_state, WorkflowTransactionTarget.CREATE_PDF)
                    st.rerun()
            with saved_col:
                if st.button("Create PDF from last saved version", use_container_width=True, key="fallback_picture_pdf_after_timeout"):
                    clear_workflow_transaction(st.session_state, WorkflowTransactionTarget.CREATE_PDF)
                    _start_synced_pdf_export()
            with cancel_col:
                if st.button("Cancel", use_container_width=True, key="cancel_picture_pdf_editor_commit"):
                    clear_workflow_transaction(st.session_state, WorkflowTransactionTarget.CREATE_PDF)
                    st.rerun()
        else:
            st.info(transaction_wait_copy(transaction))
            st.button("Create PDF", disabled=True, use_container_width=True)
            if st.button("Create PDF from last saved version", use_container_width=True):
                clear_workflow_transaction(st.session_state, WorkflowTransactionTarget.CREATE_PDF)
                _start_synced_pdf_export()
        return

    if st.button("Create PDF", type="primary", use_container_width=True):
        # Export is a hard sync boundary: image removals, replacements, uploads,
        # and crop focus changes live locally while the user reviews pictures, but
        # the PDF must be created from the exact visible editor state.
        start_workflow_transaction(st.session_state, WorkflowTransactionTarget.CREATE_PDF)
        st.rerun()
