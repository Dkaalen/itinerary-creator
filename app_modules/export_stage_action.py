from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.workflow_transactions import WorkflowTransactionTarget, clear_workflow_transaction
from app_modules.export_job_state import request_auto_pdf_create
from app_modules.saved_project_current_state import refresh_active_saved_project_current_snapshot
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_navigation import transition_workflow_stage


def enter_export_stage(
    state: MutableMapping[str, Any],
    *,
    auto_create_pdf: bool = False,
) -> WorkflowActionResult:
    """Move from picture review to export without a blocking browser handshake.

    Picture review explicitly commits the visible editor model before entering
    export, so image removals/replacements/crop focus are durable by this point.
    Clear the completed request and let the export page start the normal shared
    PDF job when ``auto_create_pdf`` is true.
    """

    clear_workflow_transaction(state, WorkflowTransactionTarget.CREATE_PDF, clear_export_job=False)
    refresh_active_saved_project_current_snapshot(state)
    if auto_create_pdf:
        request_auto_pdf_create(state)
    stage = transition_workflow_stage(state, "export")
    return WorkflowActionResult(ok=True, stage=stage, message="Export requested.")
