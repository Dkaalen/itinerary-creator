"""Workflow action coordinator for PDF export."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app_modules.export_image_validation import prepare_pdf_image_contract
from app_modules.export_identity import export_signature_for_state
from app_modules.export_pdf_artifacts import clear_pdf_artifact, current_pdf_bytes, store_current_pdf_bytes
from app_modules.export_render_context import day_image_crop_focus_for_grouped_days, pdf_render_context_for_signature
from app_modules.export_timing import record_pdf_export_stage, reset_pdf_export_timings
from project_storage.workflow_hooks import save_pdf_export
from app_modules.performance_telemetry import measure_timing, record_timing
from app_modules.pdf_export_blockers import client_safety_blocks_pdf, preview_contract_blocks_pdf
from app_modules.pdf_export_preview_file import current_preview_html_path
from app_modules.project_io import rebuild_current_preview
from app_modules.validation_gate import block_generation, render_blocking_issues, validate_for_generation
from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_pdf_file


def _current_preview_html_path() -> Path | None:
    return current_preview_html_path(st.session_state)


def _preview_contract_blocks_pdf(html: str, expected_day_count: int) -> bool:
    return preview_contract_blocks_pdf(html, expected_day_count, clear_pdf_artifact=clear_pdf_artifact)


def _client_safety_blocks_pdf(pdf_render_context, image_matches: dict, image_bank_status: dict) -> bool:
    return client_safety_blocks_pdf(
        pdf_render_context,
        image_matches,
        image_bank_status,
        clear_pdf_artifact=clear_pdf_artifact,
    )


def create_pdf_from_current_preview() -> bool:
    """Validate current state and create a durable PDF artifact when allowed."""

    if current_pdf_bytes():
        st.session_state.pdf_status = "Ready"
        return True

    reset_pdf_export_timings(st.session_state)

    with record_pdf_export_stage(st.session_state, "validate_rows"):
        validation_report = validate_for_generation(st.session_state.get("parsed_rows", []))
    if validation_report.is_blocked:
        block_generation(validation_report)
        render_blocking_issues(validation_report)
        return False

    with record_pdf_export_stage(st.session_state, "refresh_preview"):
        preview_refreshed = rebuild_current_preview(mark_pdf_dirty=False, save_html=True)
    current_preview_signature = st.session_state.get("preview_signature")
    current_pdf_signature = export_signature_for_state(st.session_state)
    if not preview_refreshed or not current_preview_signature or not current_pdf_signature:
        clear_pdf_artifact("Preview refresh failed")
        st.error("PDF export stopped because the current preview could not be refreshed.")
        return False

    html_path = _current_preview_html_path()
    if not html_path or not html_path.exists():
        st.session_state.pdf_status = "HTML preview missing"
        st.error("PDF export stopped because the HTML preview file is missing.")
        return False

    expected_day_count = len(group_rows_by_day(st.session_state.get("parsed_rows", []) or []))
    with record_pdf_export_stage(st.session_state, "validate_preview_contract"):
        preview_blocked = _preview_contract_blocks_pdf(st.session_state.get("itinerary_html", ""), expected_day_count)
    if preview_blocked:
        return False

    with record_pdf_export_stage(st.session_state, "prepare_images"):
        images_ready, current_image_bank_status, image_matches, _ = prepare_pdf_image_contract()
    if not images_ready:
        return False

    pdf_is_current = current_pdf_bytes() is not None
    if pdf_is_current:
        st.session_state.pdf_status = "Ready"
        return True

    with record_pdf_export_stage(st.session_state, "build_render_context"):
        with measure_timing(st.session_state, "build_render_context", note="pdf"):
            pdf_render_context = pdf_render_context_for_signature(current_preview_signature)
        grouped_days_for_pdf = pdf_render_context.grouped_days
        day_image_crop_focus = day_image_crop_focus_for_grouped_days(
            grouped_days_for_pdf,
            st.session_state.get("output_edits", {}) or {},
        )
    with record_pdf_export_stage(st.session_state, "client_safety_check"):
        client_safety_blocked = _client_safety_blocks_pdf(pdf_render_context, image_matches, current_image_bank_status)
    if client_safety_blocked:
        return False

    with record_pdf_export_stage(st.session_state, "render_pdf"):
        with measure_timing(st.session_state, "create_pdf"):
            pdf_path = save_pdf_file(
                html_path,
                render_document=pdf_render_context.render_document,
                color_data=pdf_render_context.colors,
                day_images=image_matches,
                day_image_crop_focus=day_image_crop_focus,
                output_edits=st.session_state.get("output_edits", {}) or {},
            )
    if pdf_path is None:
        clear_pdf_artifact("PDF failed")
        return False

    with record_pdf_export_stage(st.session_state, "store_pdf_bytes"):
        pdf_bytes = Path(pdf_path).read_bytes()
        store_current_pdf_bytes(pdf_bytes, current_pdf_signature, filename=Path(pdf_path).name)
        save_pdf_export(st.session_state, content=pdf_bytes, filename=Path(pdf_path).name)
        record_timing(st.session_state, "pdf_download_ready", 0.0)
    return True


__all__ = [
    "clear_pdf_artifact",
    "create_pdf_from_current_preview",
    "current_pdf_bytes",
    "store_current_pdf_bytes",
]
