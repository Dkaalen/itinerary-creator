"""Validate and transactionally reopen saved itinerary projects."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE, normalize_presentation_language
from app_modules.project_identity import project_payload_with_id
from app_modules.saved_project_cleaning import clean_output_edits, clean_parsed_rows
from app_modules.saved_project_image_state import apply_image_state_to_output_edits
from app_modules.saved_project_model import SavedItineraryProject
from app_modules.saved_project_restore import restore_saved_project_to_state
from app_modules.saved_project_serialization import saved_project_from_dict
from app_modules.session_state_keys import APP_STAGE_KEY
from app_modules.session_transitions import (
    capture_project_switch_baseline,
    restore_project_switch_baseline,
)
from app_modules.validation_gate import validate_for_generation
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_state import normalise_stage
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET, normalize_tone_preset
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT


def load_saved_project(
    state: MutableMapping[str, Any],
    project: SavedItineraryProject | Mapping[str, Any],
    *,
    project_id_override: str | None = None,
) -> WorkflowActionResult:
    """Load a saved project snapshot without reparsing or regenerating it."""

    if project_id_override and isinstance(project, Mapping):
        project = project_payload_with_id(project, project_id_override)
    saved_project = _coerce_saved_project(project)
    snapshot = saved_project.current_snapshot
    parsed_rows = clean_parsed_rows(snapshot.parsed_rows)
    output_edits = apply_image_state_to_output_edits(
        clean_output_edits(snapshot.output_edits),
        saved_project.image_state,
    )
    _normalize_restored_output_edits(saved_project, snapshot, output_edits)

    validation_report = validate_for_generation(parsed_rows)
    if validation_report.is_blocked:
        return WorkflowActionResult(
            ok=False,
            stage=normalise_stage(state.get(APP_STAGE_KEY, "input")),
            message="Saved project load blocked by validation issues.",
            payload={"validation_report": validation_report},
        )

    baseline = capture_project_switch_baseline(state)
    try:
        return restore_saved_project_to_state(
            state,
            saved_project=saved_project,
            parsed_rows=parsed_rows,
            output_edits=output_edits,
            validation_report=validation_report,
        )
    except Exception:
        restore_project_switch_baseline(state, baseline)
        raise


def _normalize_restored_output_edits(
    saved_project: SavedItineraryProject,
    snapshot: object,
    output_edits: dict[str, Any],
) -> None:
    output_brand = str(saved_project.output_brand or saved_project.mode or output_edits.get("output_brand") or "agent")
    output_edits["output_brand"] = output_brand
    output_edits["detail_level"] = str(
        getattr(snapshot, "detail_level", "") or output_edits.get("detail_level") or "Rich descriptive"
    )
    output_edits["day_page_layout"] = str(
        getattr(snapshot, "day_page_layout", "") or output_edits.get("day_page_layout") or DEFAULT_DAY_PAGE_LAYOUT
    )
    output_edits["presentation_language"] = normalize_presentation_language(
        output_edits.get("presentation_language") or DEFAULT_PRESENTATION_LANGUAGE
    )
    output_edits["tone_preset"] = normalize_tone_preset(output_edits.get("tone_preset") or DEFAULT_TONE_PRESET)


def _coerce_saved_project(project: SavedItineraryProject | Mapping[str, Any]) -> SavedItineraryProject:
    if isinstance(project, SavedItineraryProject):
        return project
    if isinstance(project, Mapping):
        return saved_project_from_dict(dict(project))
    raise TypeError("Saved project must be a SavedItineraryProject or payload mapping.")


__all__ = ["load_saved_project"]
