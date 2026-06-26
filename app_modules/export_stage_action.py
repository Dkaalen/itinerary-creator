from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

from app_modules.editor_commit import clear_pdf_editor_commit_request
from app_modules.export_job_state import request_auto_pdf_create
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_state import set_workflow_stage


def enter_export_stage(
    state: MutableMapping[str, Any],
    *,
    request_pdf_commit_func: Callable[[], None] | None = None,
    auto_create_pdf: bool = False,
) -> WorkflowActionResult:
    """Move from picture review to export without a blocking browser handshake.

    PDF export uses the last server-saved editor state.  Older sessions may
    still contain a pending PDF commit request from the former handshake-based
    flow; clear it so export cannot get stuck waiting for a browser message.
    The optional callback parameter is retained for compatibility with older
    imports but is intentionally not called.  When ``auto_create_pdf`` is true,
    the export page starts the normal shared PDF job after the editor has
    rendered.
    """

    clear_pdf_editor_commit_request(state)
    if auto_create_pdf:
        request_auto_pdf_create(state)
    stage = set_workflow_stage(state, "export")
    return WorkflowActionResult(ok=True, stage=stage, message="Export requested.")
