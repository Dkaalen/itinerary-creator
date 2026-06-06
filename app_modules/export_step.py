from __future__ import annotations

from pathlib import Path
import json

import streamlit as st

from ui.export_files import save_pdf_file
from ui.output_edits import apply_output_edits
from app_modules.project_io import rebuild_current_preview
from ui.picture_workflow import pictures_are_added
from itinerary_generation.common import group_rows_by_day, is_optional_row
from itinerary_generation.output_contract import validate_output_layout_contract
from itinerary_generation.quality_gate import evaluate_client_output_quality
from app_modules.validation_gate import block_generation, render_blocking_issues, validate_for_generation
from app_modules.itinerary_render_context import build_itinerary_render_context
from images.app_image_selection import (
    audit_day_image_matches,
    connect_remote_image_bank_if_missing,
    get_day_image_crop_focus,
    image_bank_status,
    select_day_images_with_overrides,
)
from images.preview_image_contract import day_image_matches_from_preview_html, merge_preview_image_contract


def _request_visual_editor_commit(target_key: str) -> None:
    next_nonce = str(int(st.session_state.get("_visual_editor_commit_counter", 0)) + 1)
    st.session_state["_visual_editor_commit_counter"] = int(next_nonce)
    st.session_state["_visual_editor_commit_nonce"] = next_nonce
    st.session_state[target_key] = next_nonce
    st.session_state["_visual_editor_export_commit_ready"] = False


def _visual_editor_export_commit_ready() -> bool:
    requested_commit_nonce = st.session_state.get("_pdf_after_visual_edit_commit_nonce")
    return bool(
        requested_commit_nonce
        and st.session_state.get("_visual_editor_export_commit_ready")
        and str(st.session_state.get("_visual_editor_last_applied_commit_nonce", "")) == str(requested_commit_nonce)
    )


def _image_grouped_days() -> dict:
    grouped_days = group_rows_by_day(st.session_state.get("parsed_rows", []) or [])
    return {
        day: [row for row in rows if not is_optional_row(row)] or list(rows)
        for day, rows in grouped_days.items()
    }


def _show_issue_list(title: str, issues) -> None:
    st.error(title)
    with st.expander("Show details"):
        for issue in issues:
            st.write(f"- {getattr(issue, 'message', issue)}")


def _create_pdf_from_current_preview() -> bool:
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
        st.session_state.pdf_signature = None
        st.session_state.pdf_status = "Needs review"
        _show_issue_list("PDF export stopped because the preview structure needs review.", blocking_contract_issues)
        return False

    image_grouped_days = _image_grouped_days()
    current_image_bank_status = image_bank_status()
    if image_grouped_days and current_image_bank_status.get("missing_full_bank"):
        current_image_bank_status = connect_remote_image_bank_if_missing()

    selected_image_matches = select_day_images_with_overrides(
        image_grouped_days,
        st.session_state.get("output_edits", {}),
    )
    preview_image_matches = day_image_matches_from_preview_html(st.session_state.get("itinerary_html", ""))
    image_matches = merge_preview_image_contract(selected_image_matches, preview_image_matches)
    current_image_bank_status = image_bank_status()
    image_issues = audit_day_image_matches(
        image_grouped_days,
        image_matches,
        st.session_state.get("output_edits", {}),
    )
    blocking_image_issues = [issue for issue in image_issues if issue.severity == "error"]
    if blocking_image_issues:
        st.session_state.pdf_signature = None
        st.session_state.pdf_status = "Needs image review"
        _show_issue_list("PDF export stopped because one or more pictures need review.", blocking_image_issues)
        return False

    current_pdf_signature = st.session_state.get("preview_signature")
    pdf_is_current = (
        bool(st.session_state.get("pdf_bytes"))
        and st.session_state.get("pdf_signature") == current_pdf_signature
    )
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
        st.session_state.pdf_status = "Blocked by output quality gate"
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
        st.session_state.pdf_bytes = None
        st.session_state.pdf_signature = None
        st.session_state.pdf_status = "PDF failed"
        return False

    st.session_state.pdf_bytes = Path(pdf_path).read_bytes()
    st.session_state.pdf_signature = current_pdf_signature
    st.session_state.pdf_status = "Ready"
    return True


def _render_secondary_downloads(app_version: str) -> None:
    project_data = {
        "app_version": app_version,
        "raw_text": st.session_state.get("last_generated_raw_text", ""),
        "output_edits": st.session_state.get("output_edits", {}),
    }
    html_path = Path(st.session_state.html_path) if st.session_state.get("html_path") else None
    col_1, col_2 = st.columns(2)
    with col_1:
        st.download_button(
            "Download project JSON",
            data=json.dumps(project_data, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="itinerary_project.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_2:
        if html_path and html_path.exists():
            with open(html_path, "rb") as html_file:
                st.download_button(
                    "Download HTML",
                    data=html_file,
                    file_name="itinerary_preview.html",
                    mime="text/html",
                    use_container_width=True,
                )
        else:
            st.button("Download HTML", disabled=True, use_container_width=True)


def render_export_step(app_version: str) -> None:
    if not st.session_state.get("itinerary_html"):
        return

    pictures_added = pictures_are_added(st.session_state.get("output_edits", {}))
    commit_ready = _visual_editor_export_commit_ready()

    if not pictures_added:
        st.warning("Add pictures before creating the final PDF.")
        return

    if st.session_state.get("_pdf_after_visual_edit_commit_nonce") and not commit_ready:
        st.info("Applying pending editor changes before creating the PDF…")
        return

    if st.session_state.get("pdf_bytes"):
        st.download_button(
            label="Download PDF",
            data=st.session_state.pdf_bytes,
            file_name="itinerary_preview.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
        st.caption("PDF is ready. Create PDF again only if you make more edits.")
        if st.button("Create PDF again", use_container_width=True):
            _request_visual_editor_commit("_pdf_after_visual_edit_commit_nonce")
            st.rerun()
    else:
        if st.button("Create PDF", type="primary", use_container_width=True):
            _request_visual_editor_commit("_pdf_after_visual_edit_commit_nonce")
            st.rerun()

    if commit_ready:
        try:
            with st.spinner("Creating client-ready PDF…"):
                ok = _create_pdf_from_current_preview()
            st.session_state["_pdf_after_visual_edit_commit_nonce"] = None
            st.session_state["_visual_editor_export_commit_ready"] = False
            st.session_state["_visual_editor_commit_nonce"] = None
            if ok:
                st.success("PDF created. Use the download button.")
                st.rerun()
        except Exception as error:
            st.session_state.pdf_signature = None
            st.session_state.pdf_status = "PDF failed"
            st.error("PDF export failed in this environment. The itinerary preview and HTML download still work.")
            with st.expander("PDF export error details"):
                st.exception(error)

    with st.expander("Other downloads", expanded=False):
        _render_secondary_downloads(app_version)
