"""Canonical restoration authority for saved itinerary workflow state."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.itinerary_render_artifact import build_and_persist_itinerary_render_artifact
from app_modules.project_file_download_cache import clear_project_file_download_cache
from app_modules.saved_project_calculator_state import restore_calculator_snapshot_to_state
from app_modules.saved_project_model import SavedItineraryProject
from app_modules.saved_project_serialization import saved_project_to_dict
from app_modules.session_state_keys import (
    DAY_PAGE_LAYOUT_KEY,
    DETAIL_LEVEL_KEY,
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
    ITINERARY_VALIDATION_REPORT_KEY,
    LAST_GENERATED_RAW_TEXT_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    PARSER_DIAGNOSTICS_KEY,
    PRESENTATION_LANGUAGE_KEY,
    RAW_TEXT_INPUT_KEY,
    STRUCTURED_INPUT_REVIEW_KEY,
    TONE_PRESET_KEY,
)
from app_modules.project_session_transitions import complete_saved_project_open
from app_modules.workflow_result import WorkflowActionResult
from app_modules.render_lifecycle import clear_pdf_artifacts
from app_modules.workflow_navigation import transition_workflow_stage
from app_modules.workflow_transients import clear_project_boundary_transients
from itinerary_generation.input_review import build_structured_input_review
from ui.picture_workflow import pictures_are_added


def restore_saved_project_to_state(
    state: MutableMapping[str, Any],
    *,
    saved_project: SavedItineraryProject,
    parsed_rows: list[dict[str, Any]],
    output_edits: dict[str, Any],
    validation_report: Any,
) -> WorkflowActionResult:
    """Replace the active itinerary project from one validated saved snapshot."""

    clear_project_boundary_transients(state)
    state[PARSED_ROWS_KEY] = parsed_rows
    state[OUTPUT_EDITS_KEY] = output_edits
    state[DETAIL_LEVEL_KEY] = output_edits["detail_level"]
    state[DAY_PAGE_LAYOUT_KEY] = output_edits["day_page_layout"]
    state[PRESENTATION_LANGUAGE_KEY] = output_edits["presentation_language"]
    state[TONE_PRESET_KEY] = output_edits["tone_preset"]
    state[LAST_GENERATED_RAW_TEXT_KEY] = saved_project.source.source_input
    state[RAW_TEXT_INPUT_KEY] = saved_project.source.source_input
    state[PARSER_DIAGNOSTICS_KEY] = []
    state[STRUCTURED_INPUT_REVIEW_KEY] = build_structured_input_review(parsed_rows, parser_diagnostics=[])
    state[ITINERARY_VALIDATION_REPORT_KEY] = validation_report
    state[ITINERARY_NAME_KEY] = saved_project.metadata.itinerary_name
    state[ITINERARY_NAME_INPUT_KEY] = saved_project.metadata.itinerary_name
    restore_calculator_snapshot_to_state(state, _calculator_snapshot_payload(saved_project.calculator_snapshot))
    clear_pdf_artifacts(state, status="Not created")
    clear_project_file_download_cache(state)

    render_signature = rebuild_restored_preview(state, parsed_rows, output_edits)
    stage = transition_workflow_stage(state, "pictures" if pictures_are_added(output_edits) else "edit")
    complete_saved_project_open(
        state,
        project_payload=saved_project_to_dict(saved_project),
        project_id=saved_project.metadata.project_id,
    )
    return WorkflowActionResult(
        ok=True,
        stage=stage,
        message="Saved project reopened.",
        payload={
            "validation_report": validation_report,
            "project_id": saved_project.metadata.project_id,
            "preview_signature": render_signature,
        },
    )


def rebuild_restored_preview(
    state: MutableMapping[str, Any],
    parsed_rows: list[dict[str, Any]],
    output_edits: dict[str, Any],
) -> str:
    """Rebuild preview artifacts from restored rows and edits without regeneration."""

    artifact = build_and_persist_itinerary_render_artifact(
        state,
        parsed_rows=parsed_rows,
        output_edits=output_edits,
        save_html=True,
    )
    return artifact.signature


def _calculator_snapshot_payload(snapshot: object) -> dict[str, Any]:
    if isinstance(snapshot, dict):
        return snapshot
    return dict(getattr(snapshot, "__dict__", {}) or {})


__all__ = ["rebuild_restored_preview", "restore_saved_project_to_state"]
