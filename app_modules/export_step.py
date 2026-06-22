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
from images.app_image_selection import destination_requests_from_rows, image_bank_status
from ui.picture_workflow import pictures_are_added
from pdf_exporter_modules.export_profiles import pdf_export_profile_options
from itinerary_generation.qa_report import (
    build_qa_report,
    persist_qa_report,
    qa_reports_dir,
    render_qa_report_json,
    render_qa_report_markdown,
)


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
        file_name=st.session_state.get("pdf_filename", "itinerary_preview.pdf"),
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        key=f"download_pdf_{location}",
    )



def _current_qa_warnings() -> list:
    warnings = []
    report = st.session_state.get("itinerary_validation_report")
    if report is not None:
        warnings.extend(getattr(report, "warnings", ()) or ())
    warnings.extend(st.session_state.get("parser_diagnostics", []) or [])
    warnings.extend(st.session_state.get("generation_overflow_warnings", []) or [])
    output_edits = st.session_state.get("output_edits", {}) or {}
    if isinstance(output_edits, dict):
        warnings.extend(output_edits.get("latest_client_output_warnings", []) or [])
    return warnings


def _render_qa_report_downloads(app_version: str) -> None:
    parsed_rows = st.session_state.get("parsed_rows", []) or []
    output_edits = st.session_state.get("output_edits", {}) or {}
    if not parsed_rows:
        st.caption("QA report is available after itinerary generation.")
        return

    report = build_qa_report(
        parsed_rows,
        output_edits,
        app_version=app_version,
        warnings=_current_qa_warnings(),
    )
    json_text = render_qa_report_json(report)
    markdown_text = render_qa_report_markdown(report)

    st.markdown("**QA report / edit learning log**")
    st.caption(
        "Use this when an activity, warning, inclusion, or page text looks wrong. "
        "Save it to shared storage for the team, or download it and send it with the latest ZIP."
    )
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.download_button(
            "Download QA Markdown",
            data=markdown_text.encode("utf-8"),
            file_name="itinerary_qa_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "Download QA JSON",
            data=json_text.encode("utf-8"),
            file_name="itinerary_qa_report.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_c:
        if st.button("Save QA report", use_container_width=True):
            paths = persist_qa_report(report)
            st.session_state["last_saved_qa_report"] = paths

    saved = st.session_state.get("last_saved_qa_report") or {}
    if saved:
        st.success(f"QA report saved to shared storage: {saved.get('markdown_path')}")
    st.caption(f"Shared QA storage: {qa_reports_dir()}")


def _render_secondary_downloads(app_version: str) -> None:
    _render_qa_report_downloads(app_version)
    st.divider()
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
    attention_messages = readiness.blocking_messages or readiness.preflight_issues
    if attention_messages and not readiness.pending_editor_commit:
        with st.expander(f"PDF preflight — {readiness.preflight_status}", expanded=bool(readiness.blocking_messages)):
            for message in attention_messages:
                st.write(f"- {message}")


def _session_state_snapshot() -> dict:
    return session_state_snapshot(st.session_state)


def _render_pdf_profile_selector() -> None:
    output_edits = st.session_state.setdefault("output_edits", {})
    profiles = list(pdf_export_profile_options())
    profile_ids = [profile["id"] for profile in profiles]
    labels = {profile["id"]: profile["label"] for profile in profiles}
    current_id = str(output_edits.get("pdf_export_profile") or profile_ids[0])
    if current_id not in profile_ids:
        current_id = profile_ids[0]
    selected = st.selectbox(
        "PDF version",
        profile_ids,
        index=profile_ids.index(current_id),
        format_func=lambda value: labels.get(value, value),
        help="Choose client, compact, or internal review export before creating the PDF.",
    )
    if selected != output_edits.get("pdf_export_profile"):
        output_edits["pdf_export_profile"] = selected
        clear_pdf_artifact("PDF version changed")


def _current_image_review_errors() -> tuple:
    """Compatibility hook: picture review no longer blocks PDF export."""

    return ()


def render_export_step(app_version: str) -> None:
    if not st.session_state.get("itinerary_html"):
        return

    required_destinations = destination_requests_from_rows(image_grouped_days_from_state(st.session_state))
    current_image_status = image_bank_status(required_destinations)
    commit_ready = visual_editor_export_commit_ready()
    image_review_errors = _current_image_review_errors()
    _render_pdf_profile_selector()
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
