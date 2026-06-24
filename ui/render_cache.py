"""Small cache-key helpers for preview/PDF rendering.

The Streamlit app reruns often. These helpers give the UI a stable way to
recognise when the itinerary content has actually changed, so expensive HTML
and PDF work can be skipped on ordinary reruns.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


# Derived/editor-review values are useful UI metadata, but they do not change
# the itinerary document itself.  Keeping them out of the render signature
# prevents warning refreshes and image-audit bookkeeping from forcing expensive
# preview/PDF rebuilds on ordinary Streamlit reruns.
DERIVED_OUTPUT_EDIT_KEYS = frozenset({
    "latest_client_output_warnings",
    "day_image_matches",
    "image_workflow_review",
    "image_review_warnings",
    "image_review_warning_count",
    "visual_editor_issue_flags",
})

DERIVED_EDITOR_DRAFT_KEYS = frozenset({
    "autosave_status",
    "save_state",
    "last_saved_at",
})


def _json_default(value: Any) -> str:
    """Return a deterministic JSON fallback for non-plain values."""
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _strip_derived_editor_draft_values(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _strip_derived_editor_draft_values(item)
            for key, item in value.items()
            if str(key) not in DERIVED_EDITOR_DRAFT_KEYS
        }
    if isinstance(value, list):
        return [_strip_derived_editor_draft_values(item) for item in value]
    return deepcopy(value)


def render_relevant_output_edits(output_edits: Any) -> Any:
    """Return only output-edit data that can affect rendered itinerary content."""

    if not isinstance(output_edits, Mapping):
        return output_edits or {}

    relevant: dict[str, Any] = {}
    for key, value in output_edits.items():
        key_text = str(key)
        if key_text in DERIVED_OUTPUT_EDIT_KEYS:
            continue
        if key_text == "editor_draft":
            relevant[key_text] = _strip_derived_editor_draft_values(value)
        else:
            relevant[key_text] = deepcopy(value)
    return relevant


def make_render_signature(parsed_rows: Any, output_edits: Any) -> str:
    """Create a stable signature for the current itinerary rendering state."""
    payload = {
        "parsed_rows": parsed_rows or [],
        "output_edits": render_relevant_output_edits(output_edits),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
