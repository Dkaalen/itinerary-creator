from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import diagnostics

from app_modules.itinerary_render_artifact import build_and_persist_itinerary_render_artifact
from app_modules.generation_settings import build_initial_output_edits, consume_generation_settings
from app_modules.parse_workflow import get_duplicate_count, parse_and_normalize_itinerary
from app_modules.performance_telemetry import measure_timing, reset_performance_telemetry
from app_modules.project_file_download_cache import clear_project_file_download_cache
from app_modules.project_workspace_revision import mark_workspace_mutated
from app_modules.saved_project_generation import create_generated_baseline_project_if_named
from app_modules.supplier_preview_cache import remember_supplier_rows_preview
from app_modules.validation_gate import validate_for_generation
from app_modules.workflow_result import WorkflowActionResult
from app_modules.render_lifecycle import clear_pdf_artifacts
from app_modules.workflow_navigation import transition_workflow_stage
from app_modules.workflow_transients import clear_project_boundary_transients
from images.image_bank import prefetch_image_bank_for_rows
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.input_review import build_structured_input_review
from app_modules.session_state_keys import (
    ITINERARY_VALIDATION_REPORT_KEY,
    LAST_GENERATED_RAW_TEXT_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    PARSER_DIAGNOSTICS_KEY,
    STRUCTURED_INPUT_REVIEW_KEY,
)


def _parse_and_review(
    state: MutableMapping[str, Any],
    raw_text: str,
    *,
    prepared_parsed_rows: list[dict] | None = None,
    prepared_parser_diagnostics: list[dict] | None = None,
) -> tuple[list[dict], Any]:
    """Parse supplier input and store review diagnostics."""

    # Single parser/generator pipeline guard: parse_and_normalize_itinerary(raw_text)
    parsed_rows = (
        [dict(row) for row in prepared_parsed_rows]
        if prepared_parsed_rows is not None
        else parse_and_normalize_itinerary(raw_text, state=state)
    )
    validation_report = validate_for_generation(parsed_rows)
    state[PARSER_DIAGNOSTICS_KEY] = (
        [dict(item) for item in prepared_parser_diagnostics]
        if prepared_parsed_rows is not None and prepared_parser_diagnostics is not None
        else diagnostics.get_warnings()
    )
    state[STRUCTURED_INPUT_REVIEW_KEY] = build_structured_input_review(
        parsed_rows,
        parser_diagnostics=state[PARSER_DIAGNOSTICS_KEY],
    )
    state[ITINERARY_VALIDATION_REPORT_KEY] = validation_report
    return parsed_rows, validation_report


def _store_generated_preview(
    state: MutableMapping[str, Any],
    *,
    parsed_rows: list[dict],
    output_edits: dict[str, Any],
) -> list[str]:
    """Build and persist the first editable itinerary preview."""

    artifact = build_and_persist_itinerary_render_artifact(
        state,
        parsed_rows=parsed_rows,
        output_edits=output_edits,
        save_html=True,
        telemetry_state=state,
    )
    state["generation_overflow_warnings"] = artifact.overflow_warnings
    return artifact.overflow_warnings


def generate_itinerary(
    state: MutableMapping[str, Any],
    raw_text: str,
    *,
    prepared_parsed_rows: list[dict] | None = None,
    prepared_parser_diagnostics: list[dict] | None = None,
) -> WorkflowActionResult:
    """Parse supplier text and build the first editable itinerary preview."""

    diagnostics.reset()
    clear_project_boundary_transients(state)
    reset_performance_telemetry(state)

    parsed_rows, validation_report = _parse_and_review(
        state,
        raw_text,
        prepared_parsed_rows=prepared_parsed_rows,
        prepared_parser_diagnostics=prepared_parser_diagnostics,
    )
    remember_supplier_rows_preview(
        state,
        raw_text,
        parsed_rows,
        parser_diagnostics=state.get(PARSER_DIAGNOSTICS_KEY) or (),
    )
    if validation_report.is_blocked:
        return WorkflowActionResult(
            ok=False,
            stage=transition_workflow_stage(state, "input"),
            message="Generation blocked by validation issues.",
            payload={"validation_report": validation_report},
        )

    grouped_days = group_rows_by_day(parsed_rows)
    duplicate_count = get_duplicate_count(raw_text, parsed_rows)
    settings = consume_generation_settings(state)
    output_edits = build_initial_output_edits(parsed_rows, grouped_days, settings)

    state[PARSED_ROWS_KEY] = parsed_rows
    state[OUTPUT_EDITS_KEY] = output_edits
    state[LAST_GENERATED_RAW_TEXT_KEY] = raw_text
    mark_workspace_mutated(state)
    clear_pdf_artifacts(state, status="Not created")
    clear_project_file_download_cache(state)

    overflow_warnings = _store_generated_preview(state, parsed_rows=parsed_rows, output_edits=output_edits)
    state["generation_duplicate_count"] = duplicate_count
    with measure_timing(state, "generate_itinerary", count=len(parsed_rows or [])):
        state["image_bank_prefetch_started"] = prefetch_image_bank_for_rows(parsed_rows)
    create_generated_baseline_project_if_named(state)
    stage = transition_workflow_stage(state, "edit")

    return WorkflowActionResult(
        ok=True,
        stage=stage,
        message="Itinerary generated.",
        payload={
            "duplicate_count": duplicate_count,
            "overflow_warnings": overflow_warnings,
            "validation_report": validation_report,
        },
    )
