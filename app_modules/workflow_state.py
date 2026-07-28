"""Workflow session defaults, reset behavior, and snapshot helpers.

Route transitions live in ``workflow_navigation``. Render invalidation lives in
``render_lifecycle``. Image matching projections live in
``image_projection_state``. Keeping this module focused prevents general session
state from becoming the owner of unrelated workflow decisions.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from typing import Any

from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE
from app_modules.route_registry import INPUT_STAGE
from app_modules.workflow_transients import PROJECT_BOUNDARY_TRANSIENT_KEYS
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from app_modules.session_state_keys import (
    ACTIVE_APP_PAGE_KEY,
    ACTIVE_PROJECT_STORAGE_ID_KEY,
    ACTIVE_SAVED_PROJECT_ID_KEY,
    ACTIVE_SAVED_PROJECT_KEY,
    APP_STAGE_KEY,
    DAY_PAGE_LAYOUT_KEY,
    DETAIL_LEVEL_KEY,
    HTML_PATH_KEY,
    ITINERARY_HTML_KEY,
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
    ITINERARY_VALIDATION_REPORT_KEY,
    LAST_GENERATED_RAW_TEXT_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    PARSER_DIAGNOSTICS_KEY,
    PENDING_PROJECT_BACKUP_IMPORT_KEY,
    PREVIEW_SIGNATURE_KEY,
    PRESENTATION_LANGUAGE_KEY,
    RAW_TEXT_INPUT_KEY,
    TONE_PRESET_KEY,
    WORKFLOW_PAGE,
)


DEFAULT_WORKFLOW_SESSION_STATE: dict[str, Any] = {
    ITINERARY_HTML_KEY: "",
    HTML_PATH_KEY: None,
    "pdf_bytes": None,
    "export_pdf_bytes": None,
    PARSED_ROWS_KEY: [],
    OUTPUT_EDITS_KEY: {},
    LAST_GENERATED_RAW_TEXT_KEY: "",
    PARSER_DIAGNOSTICS_KEY: [],
    "pdf_status": "Not created",
    PREVIEW_SIGNATURE_KEY: None,
    "pdf_signature": None,
    "export_pdf_signature": None,
    DETAIL_LEVEL_KEY: "Rich descriptive",
    DAY_PAGE_LAYOUT_KEY: DEFAULT_DAY_PAGE_LAYOUT,
    PRESENTATION_LANGUAGE_KEY: DEFAULT_PRESENTATION_LANGUAGE,
    TONE_PRESET_KEY: DEFAULT_TONE_PRESET,
    ITINERARY_VALIDATION_REPORT_KEY: None,
    APP_STAGE_KEY: INPUT_STAGE,
    ACTIVE_APP_PAGE_KEY: WORKFLOW_PAGE,
    "calculator_state": None,
}

RESET_PROJECT_KEYS = (
    ITINERARY_HTML_KEY,
    HTML_PATH_KEY,
    "pdf_bytes",
    "export_pdf_bytes",
    PARSED_ROWS_KEY,
    OUTPUT_EDITS_KEY,
    LAST_GENERATED_RAW_TEXT_KEY,
    PREVIEW_SIGNATURE_KEY,
    "_preview_render_context",
    "_preview_render_context_signature",
    "pdf_signature",
    "export_pdf_signature",
    ITINERARY_VALIDATION_REPORT_KEY,
    ACTIVE_SAVED_PROJECT_KEY,
    ACTIVE_SAVED_PROJECT_ID_KEY,
    ACTIVE_PROJECT_STORAGE_ID_KEY,
    ITINERARY_NAME_KEY,
    ITINERARY_NAME_INPUT_KEY,
    APP_STAGE_KEY,
    ACTIVE_APP_PAGE_KEY,
    PENDING_PROJECT_BACKUP_IMPORT_KEY,
    *PROJECT_BOUNDARY_TRANSIENT_KEYS,
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
        state.pop(key, None)
    from app_modules.calculator_session_state import clear_calculator_project_state

    clear_calculator_project_state(state)
    from app_modules.supplier_preview_cache import clear_supplier_preview_cache
    from app_modules.project_workspace_revision import clear_workspace_revision_state

    clear_supplier_preview_cache(state)
    clear_workspace_revision_state(state)
    for key, value in DEFAULT_WORKFLOW_SESSION_STATE.items():
        state[key] = _copy_default(value)
    if clear_raw_text:
        state[RAW_TEXT_INPUT_KEY] = ""


def session_state_snapshot(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a plain dictionary copy suitable for pure readiness checks."""

    return {key: state.get(key) for key in state.keys()}


__all__ = [
    "DEFAULT_WORKFLOW_SESSION_STATE",
    "RESET_PROJECT_KEYS",
    "ensure_workflow_defaults",
    "reset_workflow_state",
    "session_state_snapshot",
]
