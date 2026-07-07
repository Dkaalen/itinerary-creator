"""Durable PDF artifact state helpers for export workflow."""

from __future__ import annotations

import streamlit as st

from app_modules.pdf_artifact_state import (
    current_pdf_artifact,
    mirror_current_pdf_artifact,
    store_pdf_artifact,
)
from app_modules.workflow_state import clear_pdf_artifacts


def current_pdf_bytes() -> bytes | None:
    """Return current PDF bytes only when their pdf_signature matches export identity."""

    artifact = current_pdf_artifact(st.session_state)
    if artifact is None:
        return None
    mirror_current_pdf_artifact(st.session_state, artifact)
    return artifact.content


def store_current_pdf_bytes(pdf_bytes: bytes, signature: str | None, *, filename: str = "itinerary_preview.pdf") -> None:
    store_pdf_artifact(st.session_state, content=pdf_bytes, signature=signature, filename=filename)


def clear_pdf_artifact(status: str) -> None:
    clear_pdf_artifacts(st.session_state, status=status)


__all__ = ["clear_pdf_artifact", "current_pdf_bytes", "store_current_pdf_bytes"]
