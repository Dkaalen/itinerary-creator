from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_state import set_workflow_stage


def enter_export_stage(
    state: MutableMapping[str, Any], *, request_pdf_commit_func: Callable[[], None]) -> WorkflowActionResult:
    """Move from picture review to export and request a visual-editor save first."""

    request_pdf_commit_func()
    stage = set_workflow_stage(state, "export")
    return WorkflowActionResult(ok=True, stage=stage, message="Export requested.")
