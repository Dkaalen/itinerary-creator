from __future__ import annotations

from pathlib import Path
import json

import streamlit as st

from app_modules.export_actions import (
    clear_pdf_artifact,
    create_pdf_from_current_preview,
    current_pdf_bytes,
    request_pdf_creation_after_visual_editor_commit,
    visual_editor_export_commit_ready,
)
from app_modules.export_state import ExportReadiness, export_readiness_from_state
from app_modules.workflow_state import image_grouped_days_from_state, session_state_snapshot
from images.app_image_selection import audit_day_image_matches, image_bank_status, select_day_images_with_overrides
from ui.picture_workflow import pictures_are_added


def render_pdf_download_station(*, location: str = "bottom") -> None:
    """Render a durable PDF-ready download action."""

    pdf_bytes = current_pdf_bytes()
    if not pdf_bytes:
        return

    st.html(
        '<div class="pdf-ready-panel">'
        '<div><strong>PDF ready</strong><span>Your client-ready PDF has been created from the current itinerary.</span></div>'
        f'<span class="pdf-ready-location">{location}</span>'
        '</div>'
    )
    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name="itinerary_preview.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        key=f"download_pdf_{location}",
    )


def _image_grouped_days() -> dict:
    return image_grouped_days_from_state(st.session_state)


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


def _render_export_readiness_panel(readiness: ExportReadiness) -> None:
    picture_status = "Not added"
    if readiness.pictures_added:
        picture_status = "Ready" if readiness.picture_review_ready else "Needs review"
    states = [
        ("Document", "Ready" if readiness.has_document else "Missing", readiness.has_document),
        ("Pictures", picture_status, readiness.pictures_added and readiness.picture_review_ready),
        ("Image bank", "Connected" if readiness.image_bank_ready else "Missing", readiness.image_bank_ready),
        ("PDF", "Ready" if readiness.pdf_ready else "Not created", readiness.pdf_ready),
    ]
    cards = "".join(
        '<div class="export-readiness-card export-ready" data-ready="true">'
        f'<span>{label}</span><strong>{value}</strong>'
        '</div>'
        if ok
        else '<div class="export-readiness-card export-blocked" data-ready="false">'
        f'<span>{label}</span><strong>{value}</strong>'
        '</div>'
        for label, value, ok in states
    )
    st.html(
        '<div class="export-readiness-panel">'
        '<div class="export-readiness-heading">'
        f'<span>Export status</span><strong>{readiness.status_label}</strong>'
        '</div>'
        f'<div class="export-readiness-grid">{cards}</div>'
        '</div>'
    )
    if readiness.blocking_messages and not readiness.pending_editor_commit:
        with st.expander("What needs attention before PDF export?", expanded=False):
            for message in readiness.blocking_messages:
                st.write(f"- {message}")


def _session_state_snapshot() -> dict:
    return session_state_snapshot(st.session_state)


def _current_image_review_errors() -> tuple:
    output_edits = st.session_state.get("output_edits", {}) or {}
    if not pictures_are_added(output_edits):
        return ()
    image_grouped_days = _image_grouped_days()
    image_matches = select_day_images_with_overrides(image_grouped_days, output_edits)
    image_issues = audit_day_image_matches(image_grouped_days, image_matches, output_edits)
    return tuple(issue for issue in image_issues if getattr(issue, "severity", "") == "error")


def render_export_step(app_version: str) -> None:
    if not st.session_state.get("itinerary_html"):
        return

    current_image_status = image_bank_status()
    commit_ready = visual_editor_export_commit_ready()
    image_review_errors = _current_image_review_errors()
    snapshot = _session_state_snapshot()
    snapshot["image_review_error_count"] = len(image_review_errors)
    readiness = export_readiness_from_state(snapshot, current_image_status)
    _render_export_readiness_panel(readiness)

    if not readiness.pictures_added:
        st.warning("Add pictures before creating the final PDF.")
        return

    if not readiness.image_bank_ready:
        st.warning("Connect the real destination image bank before creating the final PDF.")
        return

    if not readiness.picture_review_ready:
        st.warning("Resolve blocked picture selections before creating the final PDF.")
        with st.expander("Picture issues blocking export", expanded=True):
            for issue in image_review_errors:
                st.write(f"- {getattr(issue, 'message', issue)}")
        return

    if st.session_state.get("_pdf_after_visual_edit_commit_nonce") and not commit_ready:
        st.info("Applying pending editor changes before creating the PDF…")
        return

    if current_pdf_bytes():
        render_pdf_download_station(location="bottom")
        st.caption("PDF is ready and will stay available while the current itinerary is unchanged.")
        if st.button("Create PDF again", use_container_width=True, disabled=not readiness.can_create_pdf):
            request_pdf_creation_after_visual_editor_commit()
            st.rerun()
    else:
        if st.button("Create PDF", type="primary", use_container_width=True, disabled=not readiness.can_create_pdf):
            request_pdf_creation_after_visual_editor_commit()
            st.rerun()

    if commit_ready:
        try:
            with st.spinner("Creating client-ready PDF…"):
                ok = create_pdf_from_current_preview()
            st.session_state["_pdf_after_visual_edit_commit_nonce"] = None
            st.session_state["_visual_editor_export_commit_ready"] = False
            st.session_state["_visual_editor_commit_nonce"] = None
            if ok:
                st.success("PDF created. Use the download button.")
                st.rerun()
        except Exception as error:
            clear_pdf_artifact("PDF failed")
            st.session_state["export_last_error"] = str(error)
            st.error("PDF export failed in this environment. The itinerary preview and HTML download still work.")
            with st.expander("PDF export error details"):
                st.exception(error)

    with st.expander("Other downloads", expanded=False):
        _render_secondary_downloads(app_version)
