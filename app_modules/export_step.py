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
from images.app_image_selection import destination_requests_from_rows, image_bank_status, image_bank_storage_signature
from app_modules.image_bank_status_cache import get_cached_image_bank_status
from pdf_exporter_modules.export_profiles import pdf_export_profile_options


def render_pdf_download_station(*, location: str = "bottom") -> None:
    """Render a durable PDF-ready download action."""

    pdf_bytes = current_pdf_bytes()
    if not pdf_bytes:
        return

    st.html(
        '<div class="pdf-ready-panel">'
        '<div><strong>PDF ready</strong><span>Your PDF has been created from the current itinerary.</span></div>'
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


def _render_fatal_export_blockers(readiness: ExportReadiness) -> None:
    """Show only blockers that actually prevent PDF creation."""

    if readiness.pending_editor_commit:
        st.info("Applying pending editor changes before creating the PDF…")
        return
    for message in readiness.blocking_messages:
        st.error(message)


def _session_state_snapshot() -> dict:
    return session_state_snapshot(st.session_state)


def _render_pdf_profile_selector() -> None:
    output_edits = st.session_state.setdefault("output_edits", {})
    profiles = list(pdf_export_profile_options())
    profile_ids = [profile["id"] for profile in profiles]
    labels = {profile["id"]: profile.get("selector_label") or profile["label"] for profile in profiles}
    descriptions = {profile["id"]: profile.get("description", "") for profile in profiles}
    use_cases = {profile["id"]: profile.get("use_case", "") for profile in profiles}
    current_id = str(output_edits.get("pdf_export_profile") or profile_ids[0])
    if current_id not in profile_ids:
        current_id = profile_ids[0]
    selected = st.selectbox(
        "Proposal profile",
        profile_ids,
        index=profile_ids.index(current_id),
        format_func=lambda value: labels.get(value, value),
        help="Choose the proposal/export profile before creating the PDF.",
    )
    st.caption(" · ".join(part for part in (descriptions.get(selected, ""), use_cases.get(selected, "")) if part))
    if selected != output_edits.get("pdf_export_profile"):
        output_edits["pdf_export_profile"] = selected
        clear_pdf_artifact("Proposal profile changed")



def render_export_step(app_version: str) -> None:
    if not st.session_state.get("itinerary_html"):
        return

    required_destinations = destination_requests_from_rows(image_grouped_days_from_state(st.session_state))
    current_image_status = get_cached_image_bank_status(
        st.session_state,
        required_destinations,
        image_bank_status,
        bank_signature=image_bank_storage_signature(),
    )
    commit_ready = visual_editor_export_commit_ready()
    snapshot = _session_state_snapshot()
    readiness = export_readiness_from_state(snapshot, current_image_status)
    _render_fatal_export_blockers(readiness)

    if st.session_state.get("_pdf_after_visual_edit_commit_nonce") and not commit_ready:
        return

    if current_pdf_bytes():
        render_pdf_download_station(location="bottom")

    if st.button("Create PDF", type="primary", use_container_width=True, disabled=not readiness.can_create_pdf):
        request_pdf_creation_after_visual_editor_commit()
        st.rerun()

    if commit_ready:
        try:
            with st.spinner("Creating PDF…"):
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
