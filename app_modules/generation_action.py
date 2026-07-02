from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import diagnostics

from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.parse_workflow import get_duplicate_count, get_overflow_warnings, parse_and_normalize_itinerary
from app_modules.performance_telemetry import measure_timing, reset_performance_telemetry
from app_modules.presentation_language import DEFAULT_PRESENTATION_LANGUAGE, normalize_presentation_language
from app_modules.render_context_cache import store_render_context
from app_modules.saved_project_generation import create_generated_baseline_project_if_named
from app_modules.validation_gate import validate_for_generation
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_state import clear_pdf_artifacts, set_workflow_stage
from app_modules.project_file_download_cache import clear_project_file_download_cache
from images.image_bank import prefetch_image_bank_for_rows
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.input_review import build_structured_input_review
from ui.export_files import save_html_file
from ui.output_edits import apply_output_edits, make_output_edit_state
from itinerary_generation.tone_presets import DEFAULT_TONE_PRESET, normalize_tone_preset
from ui.render_cache import make_render_signature


def generate_itinerary(state: MutableMapping[str, Any], raw_text: str) -> WorkflowActionResult:
    """Parse supplier text and build the first editable itinerary preview."""

    diagnostics.reset()
    reset_performance_telemetry(state)
    parsed_rows = parse_and_normalize_itinerary(raw_text, state=state)
    validation_report = validate_for_generation(parsed_rows)
    state["parser_diagnostics"] = diagnostics.get_warnings()
    state["structured_input_review"] = build_structured_input_review(
        parsed_rows,
        parser_diagnostics=state["parser_diagnostics"],
    )
    state["itinerary_validation_report"] = validation_report

    if validation_report.is_blocked:
        return WorkflowActionResult(
            ok=False,
            stage=set_workflow_stage(state, "input"),
            message="Generation blocked by validation issues.",
            payload={"validation_report": validation_report},
        )

    grouped_days = group_rows_by_day(parsed_rows)
    duplicate_count = get_duplicate_count(raw_text, parsed_rows)
    tone_preset = normalize_tone_preset(state.get("requested_tone_preset", state.get("tone_preset", DEFAULT_TONE_PRESET)))
    output_edits = make_output_edit_state(parsed_rows, grouped_days, tone_preset=tone_preset)
    output_brand = str(state.pop("requested_output_brand", "agent") or "agent")
    output_edits["output_brand"] = output_brand
    output_edits["presentation_language"] = normalize_presentation_language(state.get("requested_presentation_language", state.get("presentation_language", DEFAULT_PRESENTATION_LANGUAGE)))
    output_edits["tone_preset"] = tone_preset
    output_edits["color_preset"] = "Booknordics B2C" if output_brand == "booknordics_customer" else "Classic Agent"
    output_edits["allow_default_final_images"] = False

    state["parsed_rows"] = parsed_rows
    state["output_edits"] = output_edits
    state["last_generated_raw_text"] = raw_text
    clear_pdf_artifacts(state, status="Not created")
    clear_project_file_download_cache(state)

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    with measure_timing(state, "build_render_context", count=len(edited_rows or [])):
        render_context = build_itinerary_render_context(edited_rows, edited_grouped_days, output_edits)
    state["itinerary_html"] = build_itinerary_html_from_context(render_context)
    state["preview_signature"] = make_render_signature(parsed_rows, output_edits)
    store_render_context(state, signature=state["preview_signature"], context=render_context)
    state["html_path"] = save_html_file(state["itinerary_html"])
    state["generation_duplicate_count"] = duplicate_count
    state["generation_overflow_warnings"] = get_overflow_warnings(edited_grouped_days)
    with measure_timing(state, "generate_itinerary", count=len(parsed_rows or [])):
        state["image_bank_prefetch_started"] = prefetch_image_bank_for_rows(parsed_rows)
    create_generated_baseline_project_if_named(state)
    stage = set_workflow_stage(state, "edit")

    return WorkflowActionResult(
        ok=True,
        stage=stage,
        message="Itinerary generated.",
        payload={
            "duplicate_count": duplicate_count,
            "overflow_warnings": state["generation_overflow_warnings"],
            "validation_report": validation_report,
        },
    )
