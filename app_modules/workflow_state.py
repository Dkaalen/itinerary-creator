"""Central workflow/session-state helpers for the Streamlit app.

These helpers keep the app's stage and artifact rules in one place.  The
functions accept a session-like mutable mapping so core rules can be tested
without rendering Streamlit.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, MutableMapping

from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.picture_workflow import pictures_are_added
from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET
from app_modules.workflow_transients import PROJECT_BOUNDARY_TRANSIENT_KEYS
from app_modules.session_state_keys import (
    ACTIVE_APP_PAGE_KEY,
    ACTIVE_PROJECT_STORAGE_ID_KEY,
    ACTIVE_SAVED_PROJECT_ID_KEY,
    ACTIVE_SAVED_PROJECT_KEY,
    APP_STAGE_KEY,
    CALCULATOR_PAGE,
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
    WORKFLOW_STAGES,
)
from app_modules.session_transitions import normalize_workflow_stage, transition_workflow_stage


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
    APP_STAGE_KEY: "input",
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
        if key in state:
            del state[key]
    from app_modules.calculator_session_state import clear_calculator_project_state

    clear_calculator_project_state(state)
    for key, value in DEFAULT_WORKFLOW_SESSION_STATE.items():
        state[key] = _copy_default(value)
    if clear_raw_text:
        state[RAW_TEXT_INPUT_KEY] = ""


def normalise_stage(stage: str | None) -> str:
    return normalize_workflow_stage(stage)


def set_workflow_stage(state: MutableMapping[str, Any], stage: str) -> str:
    """Persist a valid workflow stage and return the normalized value."""

    return transition_workflow_stage(state, stage)


def session_stage_from_state(state: Mapping[str, Any]) -> str:
    """Resolve the visible workflow stage from current project state."""

    stage = normalise_stage(state.get(APP_STAGE_KEY, "input"))
    if not state.get(PARSED_ROWS_KEY):
        return "input"
    if stage in {"pictures", "export"} and not pictures_are_added(state.get(OUTPUT_EDITS_KEY, {}) or {}):
        return "edit"
    return stage


def clear_pdf_artifacts(state: MutableMapping[str, Any], status: str = "Not created") -> None:
    """Drop cached PDF bytes/signatures and export-only transient caches."""

    from app_modules.pdf_artifact_state import clear_pdf_artifact_state

    clear_pdf_artifact_state(state, status=status)


def mark_pdf_dirty(state: MutableMapping[str, Any], status: str = "Needs refresh") -> None:
    """Invalidate PDF artifacts and cloud-saved marker after real content changes."""

    clear_pdf_artifacts(state, status=status)
    from app_modules.project_session_cleanup import clear_project_save_marker

    clear_project_save_marker(state)


def session_state_snapshot(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a plain dict copy suitable for pure readiness checks."""

    return {key: state.get(key) for key in state.keys()}


def _day_overview_image_row(day: str, day_edit: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return a synthetic day-overview row for committed day-level edits.

    Image matching works from rows, but the visual editor stores some important
    destination signals at day level.  Adding a lightweight overview row lets the
    image matcher consume the same committed itinerary the preview/PDF use
    without mutating supplier rows or teaching the image matcher about editor
    internals.
    """

    if not isinstance(day_edit, Mapping):
        return None
    title = str(day_edit.get("title", "") or "").strip()
    city = str(day_edit.get("city", "") or "").strip()
    intro = str(day_edit.get("intro", "") or "").strip()
    if not any((title, city, intro)):
        return None
    return {
        "day": day,
        "type": "Day Overview",
        "effective_type": "Day Overview",
        "city": city,
        "title": title,
        "client_description": intro,
        "display_description": intro,
        "image_context_source": "committed_day_edit",
    }


def image_grouped_days_from_state(state: Mapping[str, Any]) -> dict:
    """Return committed image-relevant rows grouped by day.

    The picture workflow must not match against stale raw parser rows after the
    user has edited the preview.  Start from ``apply_output_edits`` and add a
    synthetic day-overview row when the committed visual editor state has
    day-level destination/title signals. Optional supplier rows are excluded
    unless they are the only rows available for the day.
    """

    from itinerary_generation.common import group_rows_by_day, is_optional_row
    from ui.output_edits import apply_output_edits

    parsed_rows = state.get(PARSED_ROWS_KEY, []) or []
    output_edits = state.get(OUTPUT_EDITS_KEY, {}) or {}
    edited_rows = apply_output_edits(parsed_rows, output_edits) if output_edits else deepcopy(parsed_rows)
    grouped_days = group_rows_by_day(edited_rows)
    day_edits = output_edits.get("days", {}) if isinstance(output_edits, Mapping) else {}

    image_grouped_days = {}
    for day, rows in grouped_days.items():
        usable_rows = [row for row in rows if not is_optional_row(row)] or list(rows)
        overview_row = _day_overview_image_row(str(day), day_edits.get(day, {}) if isinstance(day_edits, Mapping) else {})
        image_grouped_days[day] = ([overview_row] if overview_row else []) + usable_rows
    return image_grouped_days
