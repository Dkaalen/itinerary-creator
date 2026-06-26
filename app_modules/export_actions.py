"""Workflow action coordinator for PDF export."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app_modules.export_image_validation import prepare_pdf_image_contract
from app_modules.export_issue_display import show_issue_list
from app_modules.export_pdf_artifacts import clear_pdf_artifact, current_pdf_bytes, store_current_pdf_bytes
from app_modules.export_render_context import day_image_crop_focus_for_grouped_days, pdf_render_context_for_signature
from app_modules.project_io import rebuild_current_preview
from app_modules.validation_gate import block_generation, render_blocking_issues, validate_for_generation
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.output_contract import validate_output_layout_contract
from itinerary_generation.quality_gate import evaluate_client_output_quality
from ui.export_files import save_pdf_file


def _current_preview_html_path() -> Path | None:
    return Path(st.session_state.html_path) if st.session_state.get("html_path") else None


def _preview_contract_blocks_pdf(html: str, expected_day_count: int) -> bool:
    contract_issues = validate_output_layout_contract(html, expected_day_count=expected_day_count)
    blocking_contract_issues = [issue for issue in contract_issues if issue.severity == "error"]
    if not blocking_contract_issues:
        return False
    clear_pdf_artifact("Blocked by preview structure")
    show_issue_list("PDF export stopped because the preview structure is invalid.", blocking_contract_issues)
    return True


def _client_safety_blocks_pdf(pdf_render_context, image_matches: dict, image_bank_status: dict) -> bool:
    client_safety_report = evaluate_client_output_quality(
        pdf_render_context.render_document,
        day_images=image_matches,
        image_bank_status=image_bank_status,
    )
    if not client_safety_report.is_blocked:
        return False
    clear_pdf_artifact("Blocked by client safety check")
    st.error("PDF export stopped because client-facing output contains a fatal issue.")
    for issue in client_safety_report.blocking_issues:
        st.error(issue.message)
    return True


def create_pdf_from_current_preview() -> bool:
    """Validate current state and create a durable PDF artifact when allowed."""

    if current_pdf_bytes():
        st.session_state.pdf_status = "Ready"
        return True

    validation_report = validate_for_generation(st.session_state.get("parsed_rows", []))
    if validation_report.is_blocked:
        block_generation(validation_report)
        render_blocking_issues(validation_report)
        return False

    preview_refreshed = rebuild_current_preview(mark_pdf_dirty=False, save_html=True)
    current_pdf_signature = st.session_state.get("preview_signature")
    if not preview_refreshed or not current_pdf_signature:
        clear_pdf_artifact("Preview refresh failed")
        st.error("PDF export stopped because the current preview could not be refreshed.")
        return False

    html_path = _current_preview_html_path()
    if not html_path or not html_path.exists():
        st.session_state.pdf_status = "HTML preview missing"
        st.error("PDF export stopped because the HTML preview file is missing.")
        return False

    expected_day_count = len(group_rows_by_day(st.session_state.get("parsed_rows", []) or []))
    if _preview_contract_blocks_pdf(st.session_state.get("itinerary_html", ""), expected_day_count):
        return False

    images_ready, current_image_bank_status, image_matches, _ = prepare_pdf_image_contract()
    if not images_ready:
        return False

    pdf_is_current = bool(st.session_state.get("pdf_bytes")) and st.session_state.get("pdf_signature") == current_pdf_signature
    if pdf_is_current:
        st.session_state.pdf_status = "Ready"
        return True

    pdf_render_context = pdf_render_context_for_signature(current_pdf_signature)
    grouped_days_for_pdf = pdf_render_context.grouped_days
    day_image_crop_focus = day_image_crop_focus_for_grouped_days(grouped_days_for_pdf)
    if _client_safety_blocks_pdf(pdf_render_context, image_matches, current_image_bank_status):
        return False

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

    store_current_pdf_bytes(Path(pdf_path).read_bytes(), current_pdf_signature, filename=Path(pdf_path).name)
    return True


__all__ = [
    "clear_pdf_artifact",
    "create_pdf_from_current_preview",
    "current_pdf_bytes",
    "store_current_pdf_bytes",
]
