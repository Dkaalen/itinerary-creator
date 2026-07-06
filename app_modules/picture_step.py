from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header, _render_stage_actions, _stage_panel
from app_modules.export_step import render_pdf_download_station
from app_modules.picture_pdf_cta import maybe_continue_ready_pdf_transaction, render_picture_pdf_cta
from app_modules.pdf_editor_commit_gate import pdf_editor_commit_pending
from app_modules.stage_image_gateway import render_image_bank_gate
from app_modules.preview_step import _render_document_editor
from app_modules.workflow_config import STAGE_COPY


def render_picture_page(app_version: str) -> None:
    _render_app_header(app_version, stage="pictures")
    _render_stage_actions("pictures")
    render_pdf_download_station(location="top")
    if not render_image_bank_gate(st.session_state):
        return
    _stage_panel(STAGE_COPY["pictures"]["panel_title"], STAGE_COPY["pictures"]["panel_text"])

    waiting_for_pdf_commit = pdf_editor_commit_pending(st.session_state)
    _render_document_editor(pictures_active=True)
    if waiting_for_pdf_commit:
        maybe_continue_ready_pdf_transaction()

    render_picture_pdf_cta()
