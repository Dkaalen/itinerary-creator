"""Reopen saved itinerary projects through the normal workflow state."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.itinerary_name_state import ITINERARY_NAME_INPUT_KEY
from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.render_context_cache import store_render_context
from app_modules.saved_project_cleaning import clean_output_edits, clean_parsed_rows
from app_modules.saved_project_image_state import apply_image_state_to_output_edits
from app_modules.saved_project_model import SavedItineraryProject
from app_modules.saved_project_serialization import saved_project_from_dict, saved_project_to_dict
from app_modules.validation_gate import validate_for_generation
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_state import clear_pdf_artifacts, set_workflow_stage
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.input_review import build_structured_input_review
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.export_files import save_html_file
from ui.output_edits import apply_output_edits
from ui.picture_workflow import pictures_are_added
from ui.render_cache import make_render_signature

_TRANSIENT_REOPEN_KEYS = (
    "parser_diagnostics",
    "image_bank_status",
    "image_bank_gateway",
    "image_bank_prefetch_started",
    "day_image_matches",
    "image_match_unmatched_days",
    "image_workflow_review",
    "image_review_warnings",
    "image_review_warning_count",
    "generation_duplicate_count",
    "generation_overflow_warnings",
    "export_last_error",
    "_last_visual_editor_result",
    "_visual_editor_commit_nonce",
    "_visual_editor_commit_counter",
    "_visual_editor_last_applied_commit_nonce",
    "_visual_editor_export_commit_ready",
    "_visual_editor_add_pictures_commit_ready",
    "_pdf_after_visual_edit_commit_nonce",
    "_add_pictures_after_visual_edit_commit_nonce",
    "_pdf_export_job",
    "_pdf_auto_create_requested",
    "_pdf_export_timings",
)


def load_saved_project(
    state: MutableMapping[str, Any],
    project: SavedItineraryProject | Mapping[str, Any],
) -> WorkflowActionResult:
    """Load a saved project snapshot without reparsing or regenerating it."""

    saved_project = _coerce_saved_project(project)
    snapshot = saved_project.current_snapshot
    parsed_rows = clean_parsed_rows(snapshot.parsed_rows)
    output_edits = apply_image_state_to_output_edits(
        clean_output_edits(snapshot.output_edits),
        saved_project.image_state,
    )
    output_brand = str(saved_project.output_brand or saved_project.mode or output_edits.get("output_brand") or "agent")
    output_edits["output_brand"] = output_brand
    output_edits["detail_level"] = str(snapshot.detail_level or output_edits.get("detail_level") or "Rich descriptive")
    output_edits["day_page_layout"] = str(snapshot.day_page_layout or output_edits.get("day_page_layout") or DEFAULT_DAY_PAGE_LAYOUT)

    validation_report = validate_for_generation(parsed_rows)
    if validation_report.is_blocked:
        state["itinerary_validation_report"] = validation_report
        return WorkflowActionResult(
            ok=False,
            stage=set_workflow_stage(state, "input"),
            message="Saved project load blocked by validation issues.",
            payload={"validation_report": validation_report},
        )

    _clear_reopen_transients(state)
    state["parsed_rows"] = parsed_rows
    state["output_edits"] = output_edits
    state["detail_level"] = output_edits["detail_level"]
    state["day_page_layout"] = output_edits["day_page_layout"]
    state["last_generated_raw_text"] = saved_project.source.source_input
    state["raw_text_input"] = saved_project.source.source_input
    state["parser_diagnostics"] = []
    state["structured_input_review"] = build_structured_input_review(parsed_rows, parser_diagnostics=[])
    state["itinerary_validation_report"] = validation_report
    state["active_saved_project"] = saved_project_to_dict(saved_project)
    state["active_saved_project_id"] = saved_project.metadata.project_id
    state["itinerary_name"] = saved_project.metadata.itinerary_name
    state[ITINERARY_NAME_INPUT_KEY] = saved_project.metadata.itinerary_name
    clear_pdf_artifacts(state, status="Not created")

    render_signature = _rebuild_preview_state(state, parsed_rows, output_edits)
    stage = set_workflow_stage(state, "pictures" if pictures_are_added(output_edits) else "edit")

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


def _coerce_saved_project(project: SavedItineraryProject | Mapping[str, Any]) -> SavedItineraryProject:
    if isinstance(project, SavedItineraryProject):
        return project
    if isinstance(project, Mapping):
        return saved_project_from_dict(dict(project))
    raise TypeError("Saved project must be a SavedItineraryProject or payload mapping.")


def _clear_reopen_transients(state: MutableMapping[str, Any]) -> None:
    for key in _TRANSIENT_REOPEN_KEYS:
        state.pop(key, None)


def _rebuild_preview_state(
    state: MutableMapping[str, Any],
    parsed_rows: list[dict[str, Any]],
    output_edits: dict[str, Any],
) -> str:
    edited_rows = apply_output_edits(parsed_rows, output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    render_context = build_itinerary_render_context(edited_rows, edited_grouped_days, output_edits)
    render_signature = make_render_signature(parsed_rows, output_edits)
    state["itinerary_html"] = build_itinerary_html_from_context(render_context)
    state["preview_signature"] = render_signature
    store_render_context(state, signature=render_signature, context=render_context)
    state["html_path"] = save_html_file(state["itinerary_html"])
    return render_signature
