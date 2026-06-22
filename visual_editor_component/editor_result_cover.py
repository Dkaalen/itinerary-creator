"""Apply visual-editor cover and workflow payload fields."""

from visual_editor_component.editor_result_codec import _normalize_route_edit
from visual_editor_component.editor_result_sanitizer import _sanitize_cover_image_payload


def apply_cover_payload(data, output_edits):
    cover = data.get("cover", {}) or {}
    for key in ["cover_kicker", "trip_title", "trip_subtitle", "trip_dates", "destinations_line", "route_label"]:
        if key in cover:
            value = str(cover.get(key, "")).strip()
            output_edits[key] = _normalize_route_edit(value) if key == "destinations_line" else value
    for key in ["cover_image", "summary_image"]:
        if key in cover:
            output_edits[key] = _sanitize_cover_image_payload(cover.get(key) or {})


def apply_workflow_payload(data, output_edits):
    workflow = data.get("workflow", {}) or {}
    if isinstance(workflow, dict) and "pictures_added" in workflow:
        # Visual-editor payloads can be stale across the text → picture-stage
        # transition. The app workflow action is authoritative for disabling
        # pictures; editor payloads may promote False → True, but must not
        # downgrade True → False after pictures have been added.
        incoming_pictures_added = bool(workflow.get("pictures_added"))
        output_edits["pictures_added"] = bool(output_edits.get("pictures_added")) or incoming_pictures_added
