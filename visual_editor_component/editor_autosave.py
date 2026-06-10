"""Persistent autosave recovery for the visual editor."""

import streamlit as st

from itinerary_generation.draft_autosave import (
    apply_autosaved_payload_to_output_edits,
    load_autosave_payload,
)
from visual_editor_component.editor_result_applier import _stable_output_edits_snapshot
from visual_editor_component.editor_status import autosave_status


def try_apply_server_autosave(payload, output_edits, apply_result, mark_dirty=None):
    """Apply a matching server-side autosave before rendering the editor."""
    draft_id = str((output_edits or {}).get("draft_id") or payload.get("draft_id") or "").strip()
    source_signature = str((payload.get("meta") or {}).get("source_signature") or "")
    if not draft_id or st.session_state.get("_persistent_draft_recovery_checked") == draft_id:
        return False
    st.session_state["_persistent_draft_recovery_checked"] = draft_id
    saved_payload = load_autosave_payload(draft_id, source_signature=source_signature)
    if not saved_payload:
        return False
    before = _stable_output_edits_snapshot(output_edits)
    applied = apply_autosaved_payload_to_output_edits(saved_payload, output_edits, apply_result)
    if not applied:
        return False
    changed = before != _stable_output_edits_snapshot(output_edits)
    if changed and mark_dirty:
        mark_dirty()
    autosave_status({
        "ok": True,
        "draft_id": draft_id,
        "saved_at": "",
        "payload_hash": "",
    }, recovered=True)
    return changed
