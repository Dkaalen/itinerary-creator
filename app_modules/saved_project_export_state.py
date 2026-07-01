"""Build compact saved-project export status from workflow state."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app_modules.saved_project_model import SavedProjectExportState

_READY_STATUSES = frozenset({"Ready", "PDF ready"})


def export_state_from_workflow_state(
    state: Mapping[str, Any],
    *,
    saved_at: str,
    previous: SavedProjectExportState | None = None,
) -> SavedProjectExportState:
    """Return durable export metadata without storing PDF bytes."""

    pdf_status = str(state.get("pdf_status") or "Not created")
    last_exported_at = previous.last_exported_at if previous else ""
    if _current_pdf_is_ready(state, pdf_status):
        last_exported_at = saved_at
    return SavedProjectExportState(pdf_status=pdf_status, last_exported_at=last_exported_at)


def _current_pdf_is_ready(state: Mapping[str, Any], pdf_status: str) -> bool:
    signature = state.get("preview_signature")
    if not signature:
        return False
    if state.get("pdf_bytes") and state.get("pdf_signature") == signature:
        return True
    if state.get("export_pdf_bytes") and state.get("export_pdf_signature") == signature:
        return True
    return pdf_status in _READY_STATUSES and bool(state.get("pdf_signature") or state.get("export_pdf_signature"))
