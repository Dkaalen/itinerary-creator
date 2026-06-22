"""Apply visual editor save payloads to output_edits.

The public entrypoint stays here while field-specific persistence lives in
focused modules. This keeps older imports stable and makes the save pipeline
small enough to reason about safely.
"""

import streamlit as st

from itinerary_generation.draft_autosave import save_autosave_payload
from visual_editor_component.editor_result_codec import (
    _decode_visual_editor_result,
    _normalize_route_edit,
    _stable_output_edits_snapshot,
)
from visual_editor_component.editor_result_cover import apply_cover_payload, apply_workflow_payload
from visual_editor_component.editor_result_days import apply_day_payloads
from visual_editor_component.editor_result_draft import apply_editor_draft_payload
from visual_editor_component.editor_result_final_pages import apply_final_pages_payload
from visual_editor_component.editor_result_issues import apply_issue_flags_payload
from visual_editor_component.editor_result_sanitizer import _sanitize_cover_image_payload, _sanitize_editor_draft
from visual_editor_component.editor_result_summary import apply_summary_payload
from visual_editor_component.editor_status import autosave_status


def _source_signature_matches(data):
    incoming_signature = str((data.get("meta") or {}).get("source_signature") or "").strip()
    expected_signature = str(st.session_state.get("_visual_editor_current_source_signature") or "").strip()
    return not (incoming_signature and expected_signature and incoming_signature != expected_signature)


def _apply_visual_editor_payload(data, output_edits):
    apply_cover_payload(data, output_edits)
    apply_workflow_payload(data, output_edits)
    apply_summary_payload(data, output_edits)
    apply_day_payloads(data, output_edits)
    apply_final_pages_payload(data, output_edits)
    apply_editor_draft_payload(data, output_edits)
    apply_issue_flags_payload(data, output_edits)


def apply_visual_editor_result(result, output_edits, mark_dirty=None):
    """Persist visual editor edits into the normal output_edits structure."""
    if not result:
        return False
    before_snapshot = _stable_output_edits_snapshot(output_edits)
    try:
        data, commit_nonce, is_autosave = _decode_visual_editor_result(result)
    except Exception:
        st.warning("Visual editor edits could not be read. Please try saving again.")
        return False
    if not isinstance(data, dict):
        return False

    if not _source_signature_matches(data):
        st.session_state["_visual_editor_last_result_changed"] = False
        st.session_state["_visual_editor_last_result_was_autosave"] = bool(is_autosave)
        return False

    st.session_state["_visual_editor_last_result_was_autosave"] = bool(is_autosave)

    if is_autosave:
        saved_info = save_autosave_payload(data, draft_id=(output_edits or {}).get("draft_id"))
        autosave_status(saved_info)

    _apply_visual_editor_payload(data, output_edits)

    if commit_nonce:
        st.session_state["_visual_editor_last_applied_commit_nonce"] = commit_nonce

    after_snapshot = _stable_output_edits_snapshot(output_edits)
    st.session_state["_visual_editor_last_result_changed"] = before_snapshot != after_snapshot
    if mark_dirty and before_snapshot != after_snapshot:
        mark_dirty()
    return True
