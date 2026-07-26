from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

import diagnostics

from app_modules.itinerary_render_artifact import build_and_persist_itinerary_render_artifact
from app_modules.parse_workflow import parse_and_normalize_itinerary
from app_modules.validation_gate import validate_for_generation
from app_modules.workflow_result import WorkflowActionResult
from app_modules.render_lifecycle import clear_pdf_artifacts
from app_modules.workflow_navigation import transition_workflow_stage
from images.image_bank import prefetch_image_bank_for_rows
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.input_review import build_structured_input_review
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.output_edits import make_output_edit_state, refresh_generated_text_for_detail_level
from ui.picture_workflow import pictures_are_added


def load_project(
    state: MutableMapping[str, Any],
    raw_text: str,
    output_edits: Mapping[str, Any] | None,
) -> WorkflowActionResult:
    """Load a saved project through the same workflow state rules as generation."""

    diagnostics.reset()
    parsed_rows = parse_and_normalize_itinerary(raw_text)
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
            stage=transition_workflow_stage(state, "input"),
            message="Project load blocked by validation issues.",
            payload={"validation_report": validation_report},
        )

    grouped_days = group_rows_by_day(parsed_rows)
    previous_detail = (output_edits or {}).get("detail_level", "Standard client itinerary")
    loaded_edits = dict(output_edits or make_output_edit_state(parsed_rows, grouped_days))
    loaded_edits = refresh_generated_text_for_detail_level(
        parsed_rows,
        loaded_edits,
        previous_detail,
        "Rich descriptive",
    )
    loaded_edits["detail_level"] = "Rich descriptive"

    state["parsed_rows"] = parsed_rows
    state["output_edits"] = loaded_edits
    state["detail_level"] = "Rich descriptive"
    state["day_page_layout"] = loaded_edits.get(
        "day_page_layout",
        state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT),
    )
    state["last_generated_raw_text"] = raw_text
    state["raw_text_input"] = raw_text
    clear_pdf_artifacts(state, status="Not created")

    build_and_persist_itinerary_render_artifact(
        state,
        parsed_rows=parsed_rows,
        output_edits=loaded_edits,
        save_html=True,
    )
    state["image_bank_prefetch_started"] = prefetch_image_bank_for_rows(parsed_rows)
    stage = transition_workflow_stage(state, "pictures" if pictures_are_added(loaded_edits) else "edit")

    return WorkflowActionResult(
        ok=True,
        stage=stage,
        message="Editable project loaded.",
        payload={"validation_report": validation_report},
    )
