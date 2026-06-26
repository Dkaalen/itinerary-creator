from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _render_stage_actions, _stage_panel
from app_modules.export_step import render_export_step, render_pdf_download_station
from app_modules.editor_commit import clear_pdf_editor_commit_request
from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.image_gateway_ui import (
    _current_image_bank_status,
    _image_status_notice,
    _render_image_bank_gateway_repair,
)
from app_modules.preview_step import _render_document_editor
from app_modules.workflow_config import STAGE_COPY


def render_export_page(app_version: str) -> None:
    clear_pdf_editor_commit_request(st.session_state)
    _render_app_header(app_version, stage="export")
    _render_stage_actions("export")
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
    _stage_panel(STAGE_COPY["export"]["panel_title"], STAGE_COPY["export"]["panel_text"])
    _render_document_editor(pictures_active=True)

    st.html('<div class="bottom-cta"><div><strong>Ready to deliver?</strong><span>Create or download the final PDF.</span></div></div>')
    render_export_step(app_version)
