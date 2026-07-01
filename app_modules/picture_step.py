from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _render_stage_actions, _stage_panel
from app_modules.editor_commit import (
    PDF_COMMIT_REQUEST_KEY,
    clear_pdf_editor_commit_request,
    pdf_editor_commit_ready,
    request_pdf_editor_commit,
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


def _pdf_commit_pending() -> bool:
    return bool(st.session_state.get(PDF_COMMIT_REQUEST_KEY)) and not pdf_editor_commit_ready(st.session_state)


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
    if waiting_for_pdf_commit and pdf_editor_commit_ready(st.session_state):
        _start_synced_pdf_export()

    st.html('<div class="bottom-cta"><div><strong>Pictures reviewed?</strong><span>Create the final PDF from the current document.</span></div></div>')
    if current_pdf_bytes():
        return

    if pdf_editor_commit_ready(st.session_state):
        st.success("Image edits applied. Creating the PDF from the current document…")
        _start_synced_pdf_export()
        return

    if _pdf_commit_pending():
        st.info("Applying the latest picture edits before creating the PDF…")
        st.button("Create PDF", disabled=True, use_container_width=True)
        if st.button("Create PDF from last saved version", use_container_width=True):
            clear_pdf_editor_commit_request(st.session_state)
            _start_synced_pdf_export()
        return

    if st.button("Create PDF", type="primary", use_container_width=True):
        # Export is a hard sync boundary: image removals, replacements, uploads,
        # and crop focus changes live locally while the user reviews pictures, but
        # the PDF must be created from the exact visible editor state.
        request_pdf_editor_commit(st.session_state)
        st.rerun()
