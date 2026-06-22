"""Apply typed visual-editor draft payload fields."""

from itinerary_generation.editable_draft import (
    merge_editable_drafts,
    mirror_draft_to_legacy_output_edits,
    normalise_editable_draft,
)
from visual_editor_component.editor_result_sanitizer import _sanitize_editor_draft


def apply_editor_draft_payload(data, output_edits):
    if "editor_draft" not in data:
        return
    incoming_draft = normalise_editable_draft(data)
    existing_draft = output_edits.get("editor_draft") if isinstance(output_edits.get("editor_draft"), dict) else {}
    editor_draft = _sanitize_editor_draft(merge_editable_drafts(existing_draft, incoming_draft))
    mirror_draft_to_legacy_output_edits(output_edits, editor_draft)
