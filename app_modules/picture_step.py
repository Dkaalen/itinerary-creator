from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _render_stage_actions, _stage_panel
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
    _render_document_editor(pictures_active=True)

    st.html('<div class="bottom-cta"><div><strong>Pictures reviewed?</strong><span>Create the final PDF from the current document.</span></div></div>')
    if not current_pdf_bytes():
        if st.button("Create PDF", type="primary", use_container_width=True):
            enter_export_stage(st.session_state, auto_create_pdf=True)
            st.rerun()
