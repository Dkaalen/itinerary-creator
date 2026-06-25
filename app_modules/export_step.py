from __future__ import annotations

import streamlit as st

from app_modules.export_actions import (
    clear_pdf_artifact,
    create_pdf_from_current_preview,
    current_pdf_bytes,
    request_pdf_creation_after_visual_editor_commit,
    visual_editor_export_commit_ready,
)
from app_modules.export_state import ExportReadiness, export_readiness_from_state
from app_modules.editor_commit import clear_pdf_editor_commit_request
from app_modules.workflow_state import image_grouped_days_from_state, session_state_snapshot
from images.app_image_selection import destination_requests_from_rows, image_bank_status, image_bank_storage_signature
from app_modules.image_bank_status_cache import get_cached_image_bank_status


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

def _render_fatal_export_blockers(readiness: ExportReadiness) -> None:
    """Show only blockers that actually prevent PDF creation."""

    if readiness.pending_editor_commit:
        st.info("Applying pending editor changes before creating the PDF…")
        return
    for message in readiness.blocking_messages:
        st.error(message)


def _session_state_snapshot() -> dict:
    return session_state_snapshot(st.session_state)



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

    if not readiness.pdf_ready:
        if st.button("Create PDF", type="primary", use_container_width=True, disabled=not readiness.can_create_pdf):
            request_pdf_creation_after_visual_editor_commit()
            st.rerun()

    if commit_ready:
        ok = False
        try:
            with st.spinner("Creating PDF…"):
                ok = create_pdf_from_current_preview()
        except Exception as error:
            clear_pdf_artifact("PDF failed")
            st.session_state["export_last_error"] = str(error)
            st.error("PDF export failed in this environment. The editable itinerary preview is still available.")
            with st.expander("PDF export error details"):
                st.exception(error)
        finally:
            clear_pdf_editor_commit_request(st.session_state)
        if ok:
            st.success("PDF created. Use the download button.")
            st.rerun()
