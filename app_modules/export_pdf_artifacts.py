"""Durable PDF artifact state helpers for export workflow."""

from __future__ import annotations

import streamlit as st

from app_modules.export_identity import export_signature_for_state
from app_modules.workflow_state import clear_pdf_artifacts


def current_pdf_bytes() -> bytes | None:
    """Return current PDF bytes only when they match current export identity."""

    current_export_signature = export_signature_for_state(st.session_state)
    current_preview_signature = st.session_state.get("preview_signature")
    if not current_export_signature and not current_preview_signature:
        return None

    pdf_bytes = st.session_state.get("pdf_bytes")
    export_signature = st.session_state.get("export_pdf_signature")
    if pdf_bytes and export_signature and export_signature == current_export_signature:
        st.session_state.pdf_status = "Ready"
        return pdf_bytes
    if pdf_bytes and not export_signature and st.session_state.get("pdf_signature") == current_preview_signature:
        st.session_state.export_pdf_signature = current_export_signature
        st.session_state.pdf_status = "Ready"
        return pdf_bytes

    export_bytes = st.session_state.get("export_pdf_bytes")
    if export_bytes and st.session_state.get("export_pdf_signature") == current_export_signature:
        st.session_state.pdf_bytes = export_bytes
        st.session_state.pdf_signature = current_preview_signature
        st.session_state.pdf_status = "Ready"
        return export_bytes

    return None


def store_current_pdf_bytes(pdf_bytes: bytes, signature: str | None, *, filename: str = "itinerary_preview.pdf") -> None:
    preview_signature = st.session_state.get("preview_signature")
    st.session_state.pdf_bytes = pdf_bytes
    st.session_state.pdf_signature = preview_signature or signature
    st.session_state.export_pdf_bytes = pdf_bytes
    st.session_state.export_pdf_signature = signature
    st.session_state.pdf_status = "Ready"
    st.session_state.pdf_filename = filename
    st.session_state["export_last_error"] = ""


def clear_pdf_artifact(status: str) -> None:
    clear_pdf_artifacts(st.session_state, status=status)


__all__ = ["clear_pdf_artifact", "current_pdf_bytes", "store_current_pdf_bytes"]
