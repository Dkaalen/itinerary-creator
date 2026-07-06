from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _render_stage_actions, _stage_panel
from app_modules.export_step import render_export_step, render_pdf_download_station
from app_modules.preview_step import _render_document_editor
from app_modules.stage_image_gateway import render_image_bank_gate
from app_modules.workflow_config import STAGE_COPY


def render_export_page(app_version: str) -> None:
    _render_app_header(app_version, stage="export")
    _render_stage_actions("export")
    render_pdf_download_station(location="top")
    if not render_image_bank_gate(st.session_state):
        return
    _stage_panel(STAGE_COPY["export"]["panel_title"], STAGE_COPY["export"]["panel_text"])
    _render_document_editor(pictures_active=True)

    st.html('<div class="bottom-cta"><div><strong>Ready to deliver?</strong><span>Create or download the final PDF.</span></div></div>')
    render_export_step(app_version)
