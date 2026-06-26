from __future__ import annotations

import streamlit as st

from app_modules.export_actions import (
    clear_pdf_artifact,
    create_pdf_from_current_preview,
    current_pdf_bytes,
)
from app_modules.export_state import ExportReadiness, export_readiness_from_state
from app_modules.editor_commit import (
    PDF_COMMIT_REQUEST_KEY,
    clear_pdf_editor_commit_request,
    pdf_editor_commit_ready,
    request_pdf_editor_commit,
)
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

    for message in readiness.blocking_messages:
        st.error(message)


def _session_state_snapshot() -> dict:
    return session_state_snapshot(st.session_state)


def _create_pdf_now() -> bool:
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
    return ok


def _pdf_commit_pending() -> bool:
    return bool(st.session_state.get(PDF_COMMIT_REQUEST_KEY)) and not pdf_editor_commit_ready(st.session_state)


def _start_pdf_editor_commit() -> None:
    request_pdf_editor_commit(st.session_state)
    st.session_state["_pdf_create_after_editor_commit"] = True


def _create_pdf_from_committed_editor_state() -> bool:
    clear_pdf_editor_commit_request(st.session_state)
    st.session_state["_pdf_create_after_editor_commit"] = False
    return _create_pdf_now()


def render_export_step(app_version: str) -> None:
    if not st.session_state.get("itinerary_html"):
        return

    if st.session_state.get("_pdf_create_after_editor_commit") and pdf_editor_commit_ready(st.session_state):
        if _create_pdf_from_committed_editor_state():
            st.success("PDF created. Use the download button.")
            st.rerun()

    required_destinations = destination_requests_from_rows(image_grouped_days_from_state(st.session_state))
    current_image_status = get_cached_image_bank_status(
        st.session_state,
        required_destinations,
        image_bank_status,
        bank_signature=image_bank_storage_signature(),
    )
    snapshot = _session_state_snapshot()
    readiness = export_readiness_from_state(snapshot, current_image_status)
    _render_fatal_export_blockers(readiness)

    if current_pdf_bytes():
        render_pdf_download_station(location="bottom")

    if not readiness.pdf_ready:
        if _pdf_commit_pending():
            st.info("Saving the latest editor changes before creating the PDF…")
            st.button("Create PDF", disabled=True, use_container_width=True)
            if st.button("Create PDF from last saved version", use_container_width=True):
                if _create_pdf_from_committed_editor_state():
                    st.success("PDF created from the last saved itinerary. Use the download button.")
                    st.rerun()
            return

        if st.button("Create PDF", type="primary", use_container_width=True, disabled=not readiness.can_create_pdf):
            _start_pdf_editor_commit()
            st.rerun()


__all__ = ["render_export_step", "render_pdf_download_station"]
