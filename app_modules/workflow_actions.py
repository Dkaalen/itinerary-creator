"""Central workflow actions for the Streamlit itinerary flow.

The UI layer should decide what to render.  This module owns the state changes
that move a project between generation, picture review, and export stages.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

import diagnostics

from app_modules.editor_commit import (
    add_pictures_editor_commit_ready,
    clear_add_pictures_editor_commit_request,
)
from app_modules.image_gateway import connect_image_bank_for_picture_stage
from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.render_context_cache import store_render_context
from app_modules.parse_workflow import get_duplicate_count, get_overflow_warnings, parse_and_normalize_itinerary
from app_modules.validation_gate import validate_for_generation
from app_modules.workflow_state import (
    clear_pdf_artifacts,
    image_grouped_days_from_state,
    mark_pdf_dirty,
    set_workflow_stage,
)
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.input_review import build_structured_input_review
from ui.export_files import save_html_file
from images.image_bank import prefetch_image_bank_for_rows
from images.day_image_selection import normalize_day_image_matches
from images.image_workflow_review import build_image_workflow_review
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.output_edits import (
    apply_output_edits,
    make_output_edit_state,
    refresh_generated_text_for_detail_level,
)
from ui.picture_workflow import pictures_are_added, set_pictures_added
from ui.render_cache import make_render_signature


@dataclass(frozen=True)
class WorkflowActionResult:
    """Small result object returned by workflow actions."""

    ok: bool
    stage: str
    message: str = ""
    payload: dict[str, Any] | None = None


def generate_itinerary(state: MutableMapping[str, Any], raw_text: str) -> WorkflowActionResult:
    """Parse supplier text and build the first editable itinerary preview."""

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
            stage=set_workflow_stage(state, "input"),
            message="Generation blocked by validation issues.",
            payload={"validation_report": validation_report},
        )

    grouped_days = group_rows_by_day(parsed_rows)
    duplicate_count = get_duplicate_count(raw_text, parsed_rows)
    output_edits = make_output_edit_state(parsed_rows, grouped_days)
    output_edits["allow_default_final_images"] = False

    state["parsed_rows"] = parsed_rows
    state["output_edits"] = output_edits
    state["last_generated_raw_text"] = raw_text
    clear_pdf_artifacts(state, status="Not created")

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    render_context = build_itinerary_render_context(edited_rows, edited_grouped_days, output_edits)
    state["itinerary_html"] = build_itinerary_html_from_context(render_context)
    state["preview_signature"] = make_render_signature(parsed_rows, output_edits)
    store_render_context(state, signature=state["preview_signature"], context=render_context)
    state["html_path"] = save_html_file(state["itinerary_html"])
    state["generation_duplicate_count"] = duplicate_count
    state["generation_overflow_warnings"] = get_overflow_warnings(edited_grouped_days)
    state["image_bank_prefetch_started"] = prefetch_image_bank_for_rows(parsed_rows)
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
            stage=set_workflow_stage(state, "input"),
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

    edited_rows = apply_output_edits(parsed_rows, loaded_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    render_context = build_itinerary_render_context(edited_rows, edited_grouped_days, loaded_edits)
    state["itinerary_html"] = build_itinerary_html_from_context(render_context)
    state["preview_signature"] = make_render_signature(parsed_rows, loaded_edits)
    store_render_context(state, signature=state["preview_signature"], context=render_context)
    state["html_path"] = save_html_file(state["itinerary_html"])
    state["image_bank_prefetch_started"] = prefetch_image_bank_for_rows(parsed_rows)
    stage = set_workflow_stage(state, "pictures" if pictures_are_added(loaded_edits) else "edit")

    return WorkflowActionResult(
        ok=True,
        stage=stage,
        message="Editable project loaded.",
        payload={"validation_report": validation_report},
    )

def retry_image_bank_connection(
    state: MutableMapping[str, Any],
    status_func: Callable[[], Mapping[str, Any]],
    connect_func: Callable[[], Mapping[str, Any]],
) -> WorkflowActionResult:
    """Retry the separate image-bank connection without entering picture review."""

    gateway = connect_image_bank_for_picture_stage(status_func, connect_func).as_dict()
    state["image_bank_gateway"] = gateway
    state["image_bank_status"] = gateway.get("status", {})
    return WorkflowActionResult(
        ok=bool(gateway.get("ready")),
        stage=str(state.get("app_stage", "edit") or "edit"),
        message="Image bank connected." if gateway.get("ready") else gateway.get("message", "Image bank missing."),
        payload={"gateway": gateway},
    )


def enter_picture_stage(
    state: MutableMapping[str, Any],
    *,
    status_func: Callable[[], Mapping[str, Any]],
    connect_func: Callable[[], Mapping[str, Any]],
    select_images_func: Callable[[dict, Mapping[str, Any]], Mapping[str, Any]],
    audit_images_func: Callable[[dict, Mapping[str, Any], Mapping[str, Any]], list[Any] | tuple[Any, ...]],
    rebuild_preview_func: Callable[..., bool],
) -> WorkflowActionResult:
    """Connect the real image bank and activate picture review when safe."""

    output_edits = state.get("output_edits") or {}
    state["output_edits"] = output_edits
    output_edits["allow_default_final_images"] = False

    if not add_pictures_editor_commit_ready(state):
        stage = set_workflow_stage(state, "edit")
        return WorkflowActionResult(
            ok=False,
            stage=stage,
            message="Apply changes before adding pictures.",
            payload={"requires_apply_changes": True},
        )

    gateway = connect_image_bank_for_picture_stage(status_func, connect_func).as_dict()
    state["image_bank_gateway"] = gateway
    state["image_bank_status"] = gateway.get("status", {})

    if not gateway.get("ready"):
        set_pictures_added(output_edits, False)
        state["image_review_warning_count"] = 0
        clear_pdf_artifacts(state, status="Image bank missing")
        stage = set_workflow_stage(state, "edit")
        return WorkflowActionResult(
            ok=False,
            stage=stage,
            message=gateway.get("message", "Image bank missing."),
            payload={"gateway": gateway},
        )

    image_grouped_days = image_grouped_days_from_state(state)
    # Select before marking the workflow successful.  The image bank may be
    # connected while still producing zero usable matches because destination
    # names, folder aliases or bank contents do not line up.  In that case the
    # user needs an actionable warning instead of a false "Pictures added" state.
    matches = normalize_day_image_matches(select_images_func(image_grouped_days, output_edits))
    matched_days = [day for day, match in (matches or {}).items() if isinstance(match, Mapping) and (match.get("path") or match.get("data_uri"))]
    unmatched_days = [day for day in (image_grouped_days or {}) if day not in matched_days]

    if not matched_days:
        set_pictures_added(output_edits, False)
        # Derived audit metadata only. Durable user choices live in day_images.
        output_edits["day_image_matches"] = dict(matches or {})
        output_edits["image_match_unmatched_days"] = unmatched_days
        image_review = build_image_workflow_review(image_grouped_days, matches, ())
        state["image_workflow_review"] = image_review.as_dict()
        output_edits["image_workflow_review"] = image_review.as_dict()
        state["image_review_warning_count"] = max(1, len(unmatched_days))
        clear_pdf_artifacts(state, status="No destination pictures matched")
        stage = set_workflow_stage(state, "edit")
        return WorkflowActionResult(
            ok=False,
            stage=stage,
            message="Image bank connected, but no destination pictures matched. Check destination names and image-bank folders.",
            payload={"gateway": gateway, "matches": matches, "unmatched_days": unmatched_days},
        )

    set_pictures_added(output_edits, True)
    # Derived audit metadata only. Durable user choices live in day_images.
    output_edits["day_image_matches"] = dict(matches or {})
    output_edits["image_match_unmatched_days"] = unmatched_days
    editor_draft = output_edits.get("editor_draft")
    if isinstance(editor_draft, dict):
        workflow = editor_draft.setdefault("workflow", {})
        if isinstance(workflow, dict):
            workflow["pictures_added"] = True
    warnings = audit_images_func(image_grouped_days, matches, output_edits)
    image_review = build_image_workflow_review(image_grouped_days, matches, warnings)
    state["image_workflow_review"] = image_review.as_dict()
    output_edits["image_workflow_review"] = image_review.as_dict()
    state["image_review_warning_count"] = len(
        [warning for warning in warnings if getattr(warning, "severity", "") == "error"]
    )
    state.pop("image_bank_gateway", None)
    clear_add_pictures_editor_commit_request(state)
    mark_pdf_dirty(state, status="Needs refresh")
    rebuild_preview_func(mark_pdf_dirty=True, force=True, save_html=True)
    stage = set_workflow_stage(state, "pictures")
    message = "Pictures added." if not unmatched_days else f"Pictures added. {len(unmatched_days)} day(s) still need image review."
    return WorkflowActionResult(ok=True, stage=stage, message=message, payload={"matches": matches, "unmatched_days": unmatched_days})


def enter_export_stage(
    state: MutableMapping[str, Any], *, request_pdf_commit_func: Callable[[], None]) -> WorkflowActionResult:
    """Move from picture review to export and request a visual-editor save first."""

    request_pdf_commit_func()
    stage = set_workflow_stage(state, "export")
    return WorkflowActionResult(ok=True, stage=stage, message="Export requested.")
