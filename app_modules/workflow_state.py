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
from ui.output_edits import apply_output_edits
from ui.picture_workflow import pictures_are_added
from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE
from app_modules.calculator_session_state import clear_calculator_project_state
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET
from app_modules.workflow_transients import PROJECT_BOUNDARY_TRANSIENT_KEYS


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
    "presentation_language": DEFAULT_PRESENTATION_LANGUAGE,
    "tone_preset": DEFAULT_TONE_PRESET,
    "itinerary_validation_report": None,
    "app_stage": "input",
    "active_app_page": "workflow",
    "calculator_state": None,
}

RESET_PROJECT_KEYS = (
    "itinerary_html",
    "html_path",
    "pdf_bytes",
    "export_pdf_bytes",
    "parsed_rows",
    "output_edits",
    "last_generated_raw_text",
    "preview_signature",
    "_preview_render_context",
    "_preview_render_context_signature",
    "pdf_signature",
    "export_pdf_signature",
    "itinerary_validation_report",
    "active_saved_project",
    "active_saved_project_id",
    "active_project_storage_id",
    "itinerary_name",
    "itinerary_name_input",
    "app_stage",
    "active_app_page",
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
    clear_calculator_project_state(state)
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

    parsed_rows = state.get("parsed_rows", []) or []
    output_edits = state.get("output_edits", {}) or {}
    edited_rows = apply_output_edits(parsed_rows, output_edits) if output_edits else deepcopy(parsed_rows)
    grouped_days = group_rows_by_day(edited_rows)
    day_edits = output_edits.get("days", {}) if isinstance(output_edits, Mapping) else {}

    image_grouped_days = {}
    for day, rows in grouped_days.items():
        usable_rows = [row for row in rows if not is_optional_row(row)] or list(rows)
        overview_row = _day_overview_image_row(str(day), day_edits.get(day, {}) if isinstance(day_edits, Mapping) else {})
        image_grouped_days[day] = ([overview_row] if overview_row else []) + usable_rows
    return image_grouped_days
