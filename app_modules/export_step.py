from __future__ import annotations

import streamlit as st

from app_modules.export_actions import current_pdf_bytes
from app_modules.export_download_station import render_pdf_download_station as _render_pdf_download_station
from app_modules.pdf_creation_request import (
    clear_stale_pdf_editor_state,
    pdf_editor_commit_pending,
    pdf_transaction_state,
    queue_synced_pdf_creation,
    request_pdf_creation,
)
from app_modules.workflow_transactions import (
    WorkflowTransactionTarget,
    clear_workflow_transaction,
    retry_workflow_transaction,
    transaction_timeout_copy,
    transaction_wait_copy,
)
from app_modules.export_job_state import (
    auto_pdf_create_requested,
    consume_auto_pdf_create_request,
    current_export_job,
    reset_export_job,
)
from app_modules.export_state import ExportReadiness, export_readiness_from_state
from app_modules.export_readiness_ui import export_readiness_panel_html
from app_modules.workflow_state import image_grouped_days_from_state, session_state_snapshot
from images.app_image_selection import destination_requests_from_rows, image_bank_status, image_bank_storage_signature
from app_modules.image_bank_status_cache import get_cached_image_bank_status


def render_pdf_download_station(*, location: str = "bottom") -> None:
    """Compatibility facade for the shared PDF download station."""

    _render_pdf_download_station(location=location)



def _render_fatal_export_blockers(readiness: ExportReadiness) -> None:
    """Show only blockers that actually prevent PDF creation."""

    for message in readiness.blocking_messages:
        st.error(message)


def _session_state_snapshot() -> dict:
    return session_state_snapshot(st.session_state)

def _current_image_bank_status_for_export() -> dict:
    required_destinations = destination_requests_from_rows(image_grouped_days_from_state(st.session_state))
    return get_cached_image_bank_status(
        st.session_state,
        required_destinations,
        image_bank_status,
        bank_signature=image_bank_storage_signature(),
    )


def render_export_step(app_version: str) -> None:
    if not st.session_state.get("itinerary_html"):
        return

    current_image_status = _current_image_bank_status_for_export()
    snapshot = _session_state_snapshot()
    readiness = export_readiness_from_state(snapshot, current_image_status)
    st.html(export_readiness_panel_html(readiness))
    _render_fatal_export_blockers(readiness)

    if current_pdf_bytes():
        render_pdf_download_station(location="bottom")

    if readiness.pdf_ready:
        return

    auto_create = auto_pdf_create_requested(st.session_state)
    commit_pending = pdf_editor_commit_pending()
    if auto_create and commit_pending:
        transaction = pdf_transaction_state()
        if transaction.timed_out:
            st.warning(transaction_timeout_copy(transaction))
            st.caption("Retry the save, create from the last saved version, or cancel this PDF request.")
            retry_col, saved_col, cancel_col = st.columns(3)
            with retry_col:
                if st.button("Retry save", type="primary", use_container_width=True, key="retry_export_pdf_editor_commit"):
                    retry_workflow_transaction(st.session_state, WorkflowTransactionTarget.CREATE_PDF, auto_create_pdf=True)
                    st.rerun()
            with saved_col:
                if st.button("Create PDF from last saved version", use_container_width=True, key="fallback_export_pdf_after_timeout", disabled=not readiness.can_create_pdf):
                    consume_auto_pdf_create_request(st.session_state)
                    clear_workflow_transaction(st.session_state, WorkflowTransactionTarget.CREATE_PDF)
                    request_pdf_creation()
            with cancel_col:
                if st.button("Cancel", use_container_width=True, key="cancel_export_pdf_editor_commit"):
                    clear_stale_pdf_editor_state()
                    st.rerun()
        else:
            st.info(transaction_wait_copy(pdf_transaction_state()))
            st.button("Create PDF", disabled=True, use_container_width=True)
        return
    if auto_create and readiness.can_create_pdf:
        consume_auto_pdf_create_request(st.session_state)
        request_pdf_creation()
        return
    if auto_create:
        consume_auto_pdf_create_request(st.session_state)
        reset_export_job(st.session_state)
        st.warning("PDF creation was stopped because the document is not ready. Fix the blocker above, then click Create PDF again.")

    job = current_export_job(st.session_state)
    if job.failed and job.error:
        st.warning("The last PDF attempt did not complete. You can retry without restarting the itinerary.")

    if st.button("Create PDF", type="primary", use_container_width=True, disabled=not readiness.can_create_pdf):
        queue_synced_pdf_creation()


__all__ = ["render_export_step", "render_pdf_download_station"]
