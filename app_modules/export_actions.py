"""Workflow actions for PDF export.

The Streamlit export screen should mostly render controls and status. This module
owns the state-heavy export actions: editor-save coordination, durable PDF bytes,
preview validation, image validation, quality gate checks, and final PDF creation.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.project_io import rebuild_current_preview
from app_modules.validation_gate import block_generation, render_blocking_issues, validate_for_generation
from app_modules.workflow_state import clear_pdf_artifacts, image_grouped_days_from_state
from images.app_image_selection import (
    connect_remote_image_bank_if_missing,
    get_day_image_crop_focus,
    image_bank_status,
    select_day_images_with_overrides,
)
from images.preview_image_contract import day_image_matches_from_preview_html, merge_preview_image_contract
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.output_contract import validate_output_layout_contract
from itinerary_generation.quality_gate import evaluate_client_output_quality
from ui.export_files import save_pdf_file
from ui.output_edits import apply_output_edits


def _request_visual_editor_commit(target_key: str) -> None:
    next_nonce = str(int(st.session_state.get("_visual_editor_commit_counter", 0)) + 1)
    st.session_state["_visual_editor_commit_counter"] = int(next_nonce)
    st.session_state["_visual_editor_commit_nonce"] = next_nonce
    st.session_state[target_key] = next_nonce
    st.session_state["_visual_editor_export_commit_ready"] = False


def request_pdf_creation_after_visual_editor_commit() -> None:
    """Ask the visual editor to save before PDF creation starts."""

    _request_visual_editor_commit("_pdf_after_visual_edit_commit_nonce")


def visual_editor_export_commit_ready() -> bool:
    requested_commit_nonce = st.session_state.get("_pdf_after_visual_edit_commit_nonce")
    return bool(
        requested_commit_nonce
        and st.session_state.get("_visual_editor_export_commit_ready")
        and str(st.session_state.get("_visual_editor_last_applied_commit_nonce", "")) == str(requested_commit_nonce)
    )


def current_pdf_bytes() -> bytes | None:
    """Return current PDF bytes from durable export state."""

    current_signature = st.session_state.get("preview_signature")
    pdf_bytes = st.session_state.get("pdf_bytes")
    if pdf_bytes and st.session_state.get("pdf_signature") == current_signature:
        return pdf_bytes

    export_bytes = st.session_state.get("export_pdf_bytes")
    if export_bytes and st.session_state.get("export_pdf_signature") == current_signature:
        st.session_state.pdf_bytes = export_bytes
        st.session_state.pdf_signature = current_signature
        st.session_state.pdf_status = "Ready"
        return export_bytes

    return None


def store_current_pdf_bytes(pdf_bytes: bytes, signature: str | None) -> None:
    st.session_state.pdf_bytes = pdf_bytes
    st.session_state.pdf_signature = signature
    st.session_state.export_pdf_bytes = pdf_bytes
    st.session_state.export_pdf_signature = signature
    st.session_state.pdf_status = "Ready"
    st.session_state["export_last_error"] = ""


def clear_pdf_artifact(status: str) -> None:
    clear_pdf_artifacts(st.session_state, status=status)


def _image_grouped_days() -> dict:
    return image_grouped_days_from_state(st.session_state)


def _show_issue_list(title: str, issues) -> None:
    st.error(title)
    with st.expander("Show details"):
        for issue in issues:
            st.write(f"- {getattr(issue, 'message', issue)}")


def create_pdf_from_current_preview() -> bool:
    """Validate current state and create a durable PDF artifact when allowed."""

    validation_report = validate_for_generation(st.session_state.get("parsed_rows", []))
    if validation_report.is_blocked:
        block_generation(validation_report)
        render_blocking_issues(validation_report)
        return False

    rebuild_current_preview(mark_pdf_dirty=False, save_html=True)
    html_path = Path(st.session_state.html_path) if st.session_state.get("html_path") else None
    if not html_path or not html_path.exists():
        st.session_state.pdf_status = "HTML preview missing"
        st.error("PDF export stopped because the HTML preview file is missing.")
        return False

    expected_day_count = len(group_rows_by_day(st.session_state.get("parsed_rows", []) or []))
    contract_issues = validate_output_layout_contract(
        st.session_state.get("itinerary_html", ""),
        expected_day_count=expected_day_count,
    )
    blocking_contract_issues = [issue for issue in contract_issues if issue.severity == "error"]
    if blocking_contract_issues:
        clear_pdf_artifact("Needs review")
        _show_issue_list("PDF export stopped because the preview structure needs review.", blocking_contract_issues)
        return False

    image_grouped_days = _image_grouped_days()
    current_image_bank_status = image_bank_status()
    if image_grouped_days and current_image_bank_status.get("missing_full_bank"):
        current_image_bank_status = connect_remote_image_bank_if_missing()
    if not image_bank_is_ready_for_client_pictures(current_image_bank_status):
        clear_pdf_artifact("Image bank missing")
        st.error(current_image_bank_status.get("blocking_message") or "PDF export stopped because the real destination image bank is missing.")
        return False

    selected_image_matches = select_day_images_with_overrides(
        image_grouped_days,
        st.session_state.get("output_edits", {}),
    )
    preview_image_matches = day_image_matches_from_preview_html(st.session_state.get("itinerary_html", ""))
    image_matches = merge_preview_image_contract(selected_image_matches, preview_image_matches)
    current_image_bank_status = image_bank_status()

    current_pdf_signature = st.session_state.get("preview_signature")
    pdf_is_current = bool(st.session_state.get("pdf_bytes")) and st.session_state.get("pdf_signature") == current_pdf_signature
    if pdf_is_current:
        st.session_state.pdf_status = "Ready"
        return True

    edited_rows_for_pdf = apply_output_edits(
        st.session_state.get("parsed_rows", []) or [],
        st.session_state.get("output_edits", {}) or {},
    )
    grouped_days_for_pdf = group_rows_by_day(edited_rows_for_pdf)
    pdf_render_context = build_itinerary_render_context(
        edited_rows_for_pdf,
        grouped_days_for_pdf,
        st.session_state.get("output_edits", {}) or {},
    )
    day_image_crop_focus = {
        day: get_day_image_crop_focus(st.session_state.get("output_edits", {}) or {}, day)
        for day in grouped_days_for_pdf
    }
    client_quality_report = evaluate_client_output_quality(
        pdf_render_context.render_document,
        day_images=image_matches,
        image_bank_status=current_image_bank_status,
    )
    if client_quality_report.is_blocked:
        clear_pdf_artifact("Blocked by output quality gate")
        for issue in client_quality_report.blocking_issues:
            st.error(issue.message)
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

    store_current_pdf_bytes(Path(pdf_path).read_bytes(), current_pdf_signature)
    return True
