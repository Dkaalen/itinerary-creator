from __future__ import annotations

import streamlit as st

from app_modules.export_actions import (
    clear_pdf_artifact,
    create_pdf_from_current_preview,
    current_pdf_bytes,
)
from app_modules.export_editor_save import clear_pdf_editor_save
from app_modules.export_job_state import (
    consume_auto_pdf_create_request,
    current_export_job,
    mark_export_failed,
    mark_export_ready,
    mark_exporting,
)
from app_modules.export_state import ExportReadiness, export_readiness_from_state
from app_modules.workflow_state import image_grouped_days_from_state, session_state_snapshot
from images.app_image_selection import destination_requests_from_rows, image_bank_status
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
    mark_exporting(st.session_state, signature=st.session_state.get("preview_signature"))
    ok = False
    try:
        with st.spinner("Creating PDF…"):
            ok = create_pdf_from_current_preview()
    except Exception as error:
        clear_pdf_artifact("PDF failed")
        mark_export_failed(st.session_state, error=str(error))
        st.session_state["export_last_error"] = str(error)
        st.error("PDF export failed in this environment. The editable itinerary preview is still available.")
        with st.expander("PDF export error details"):
            st.exception(error)
        return False
    if ok:
        mark_export_ready(st.session_state, signature=st.session_state.get("preview_signature"))
    else:
        mark_export_failed(st.session_state, error=st.session_state.get("pdf_status") or "PDF export failed.")
    return ok


def _request_pdf_creation() -> None:
    """Create the PDF from the current server-owned preview state.

    The visual editor autosaves text/image changes separately.  PDF creation must
    not start a browser commit handshake here, because missing component messages
    were the source of long waits and broken export jobs.
    """

    clear_pdf_editor_save(st.session_state)
    if _create_pdf_now():
        st.success("PDF created. Use the download button.")
        st.rerun()


def _current_image_bank_status_for_export() -> dict:
    required_destinations = destination_requests_from_rows(image_grouped_days_from_state(st.session_state))
    return get_cached_image_bank_status(st.session_state, required_destinations, image_bank_status)


def render_export_step(app_version: str) -> None:
    if not st.session_state.get("itinerary_html"):
        return

    current_image_status = _current_image_bank_status_for_export()
    snapshot = _session_state_snapshot()
    readiness = export_readiness_from_state(snapshot, current_image_status)
    _render_fatal_export_blockers(readiness)

    if current_pdf_bytes():
        render_pdf_download_station(location="bottom")

    if readiness.pdf_ready:
        return

    auto_create = consume_auto_pdf_create_request(st.session_state)
    if auto_create and readiness.can_create_pdf:
        _request_pdf_creation()
        return

    job = current_export_job(st.session_state)
    if job.failed and job.error:
        st.warning("The last PDF attempt did not complete. You can retry without restarting the itinerary.")

    if st.button("Create PDF", type="primary", use_container_width=True, disabled=not readiness.can_create_pdf):
        _request_pdf_creation()


__all__ = ["render_export_step", "render_pdf_download_station"]
