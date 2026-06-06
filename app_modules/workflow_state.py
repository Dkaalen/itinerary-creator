"""Central workflow/session-state helpers for the Streamlit app.

These helpers keep the app's stage and artifact rules in one place.  The
functions accept a session-like mutable mapping so core rules can be tested
without rendering Streamlit.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, MutableMapping

from itinerary_generation.common import group_rows_by_day, is_optional_row
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.picture_workflow import pictures_are_added


WORKFLOW_STAGES = ("input", "edit", "pictures", "export")
PDF_ARTIFACT_KEYS = (
    "pdf_bytes",
    "export_pdf_bytes",
    "pdf_signature",
    "export_pdf_signature",
)

DEFAULT_WORKFLOW_SESSION_STATE: dict[str, Any] = {
    "itinerary_html": "",
    "html_path": None,
    "pdf_bytes": None,
    "export_pdf_bytes": None,
    "parsed_rows": [],
    "output_edits": {},
    "last_generated_raw_text": "",
    "parser_diagnostics": [],
    "pdf_status": "Not created",
    "preview_signature": None,
    "pdf_signature": None,
    "export_pdf_signature": None,
    "detail_level": "Rich descriptive",
    "day_page_layout": DEFAULT_DAY_PAGE_LAYOUT,
    "itinerary_validation_report": None,
    "app_stage": "input",
}

RESET_PROJECT_KEYS = (
    "itinerary_html",
    "html_path",
    "pdf_bytes",
    "export_pdf_bytes",
    "parsed_rows",
    "output_edits",
    "last_generated_raw_text",
    "parser_diagnostics",
    "preview_signature",
    "pdf_signature",
    "export_pdf_signature",
    "_last_visual_editor_result",
    "_visual_editor_commit_nonce",
    "_visual_editor_commit_counter",
    "_visual_editor_last_applied_commit_nonce",
    "_visual_editor_export_commit_ready",
    "_visual_editor_add_pictures_commit_ready",
    "_pdf_after_visual_edit_commit_nonce",
    "_add_pictures_after_visual_edit_commit_nonce",
    "itinerary_validation_report",
    "app_stage",
    "image_bank_status",
    "image_bank_gateway",
    "image_review_warning_count",
    "image_review_error_count",
    "generation_duplicate_count",
    "generation_overflow_warnings",
    "export_last_error",
)


def _copy_default(value: Any) -> Any:
    return deepcopy(value)


def ensure_workflow_defaults(state: MutableMapping[str, Any]) -> None:
    """Populate missing workflow keys without overwriting an active project."""

    for key, value in DEFAULT_WORKFLOW_SESSION_STATE.items():
        if key not in state:
            state[key] = _copy_default(value)


def reset_workflow_state(state: MutableMapping[str, Any], *, clear_raw_text: bool = True) -> None:
    """Return a session-like mapping to a clean input-stage project state."""

    for key in RESET_PROJECT_KEYS:
        if key in state:
            del state[key]
    for key, value in DEFAULT_WORKFLOW_SESSION_STATE.items():
        state[key] = _copy_default(value)
    if clear_raw_text:
        state["raw_text_input"] = ""


def normalise_stage(stage: str | None) -> str:
    value = str(stage or "input")
    return value if value in WORKFLOW_STAGES else "input"


def set_workflow_stage(state: MutableMapping[str, Any], stage: str) -> str:
    """Persist a valid workflow stage and return the normalized value."""

    normalized = normalise_stage(stage)
    state["app_stage"] = normalized
    return normalized


def session_stage_from_state(state: Mapping[str, Any]) -> str:
    """Resolve the visible workflow stage from current project state."""

    stage = normalise_stage(state.get("app_stage", "input"))
    if not state.get("parsed_rows"):
        return "input"
    if stage in {"pictures", "export"} and not pictures_are_added(state.get("output_edits", {}) or {}):
        return "edit"
    return stage


def clear_pdf_artifacts(state: MutableMapping[str, Any], status: str = "Not created") -> None:
    """Drop all cached PDF bytes/signatures and set a user-facing status."""

    for key in PDF_ARTIFACT_KEYS:
        state[key] = None
    state["pdf_status"] = status


def mark_pdf_dirty(state: MutableMapping[str, Any], status: str = "Needs refresh") -> None:
    """Invalidate durable PDF artifacts after real content or picture changes."""

    clear_pdf_artifacts(state, status=status)


def session_state_snapshot(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a plain dict copy suitable for pure readiness checks."""

    return {key: state.get(key) for key in state.keys()}


def image_grouped_days_from_state(state: Mapping[str, Any]) -> dict:
    """Return image-relevant rows grouped by day, excluding optional rows when possible."""

    grouped_days = group_rows_by_day(state.get("parsed_rows", []) or [])
    return {
        day: [row for row in rows if not is_optional_row(row)] or list(rows)
        for day, rows in grouped_days.items()
    }
