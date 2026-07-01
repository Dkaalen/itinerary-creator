from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from typing import Any

from app_modules.editor_commit import add_pictures_editor_commit_ready, clear_add_pictures_editor_commit_request
from app_modules.saved_project_current_state import refresh_active_saved_project_current_snapshot
from app_modules.image_gateway import connect_image_bank_for_picture_stage
from app_modules.workflow_result import WorkflowActionResult
from app_modules.workflow_state import clear_pdf_artifacts, image_grouped_days_from_state, mark_pdf_dirty, set_workflow_stage
from images.day_image_selection import normalize_day_image_matches
from images.image_workflow_review import build_image_workflow_review
from ui.picture_workflow import set_pictures_added


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
    for derived_key in ("day_image_matches", "image_match_unmatched_days", "image_workflow_review"):
        output_edits.pop(derived_key, None)
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
        state["day_image_matches"] = dict(matches or {})
        state["image_match_unmatched_days"] = unmatched_days
        image_review = build_image_workflow_review(image_grouped_days, matches, ())
        state["image_workflow_review"] = image_review.as_dict()
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
    state["day_image_matches"] = dict(matches or {})
    state["image_match_unmatched_days"] = unmatched_days
    editor_draft = output_edits.get("editor_draft")
    if isinstance(editor_draft, dict):
        workflow = editor_draft.setdefault("workflow", {})
        if isinstance(workflow, dict):
            workflow["pictures_added"] = True
    warnings = audit_images_func(image_grouped_days, matches, output_edits)
    image_review = build_image_workflow_review(image_grouped_days, matches, warnings)
    state["image_workflow_review"] = image_review.as_dict()
    state["image_review_warning_count"] = len(
        [warning for warning in warnings if getattr(warning, "severity", "") == "error"]
    )
    state.pop("image_bank_gateway", None)
    clear_add_pictures_editor_commit_request(state)
    mark_pdf_dirty(state, status="Needs refresh")
    rebuild_preview_func(mark_pdf_dirty=True, force=True, save_html=True)
    refresh_active_saved_project_current_snapshot(state)
    stage = set_workflow_stage(state, "pictures")
    message = "Pictures added." if not unmatched_days else f"Pictures added. {len(unmatched_days)} day(s) still need image review."
    return WorkflowActionResult(ok=True, stage=stage, message=message, payload={"matches": matches, "unmatched_days": unmatched_days})
