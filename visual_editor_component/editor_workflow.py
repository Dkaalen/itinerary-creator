"""Visual editor workflow facade.

The heavy responsibilities are split into focused modules:
- editor_payload_builder builds the component payload.
- editor_result_applier persists save/autosave payloads.
- editor_autosave restores matching server-side autosaves.

This module keeps the public import path stable for Streamlit pages and tests.
"""

import streamlit as st

from app_modules.editor_commit import (
    ADD_PICTURES_COMMIT_REQUEST_KEY,
    ADD_PICTURES_COMMIT_READY_KEY,
    PDF_COMMIT_REQUEST_KEY,
    PDF_COMMIT_READY_KEY,
)
from app_modules.saved_project_current_state import refresh_active_saved_project_current_snapshot
from app_modules.performance_telemetry import measure_timing
from visual_editor_component.editor_autosave import try_apply_server_autosave
from visual_editor_component.editor_status import autosave_status as _autosave_status
from visual_editor_component.editor_bridge import render_visual_page_editor
from visual_editor_component.editor_commit_signal import build_editor_commit_signal_payload
from visual_editor_component.editor_payload_builder import (
    _build_generated_exclusions_html,
    _build_generated_inclusion_page_htmls,
    _build_generated_inclusion_sections,
    _build_generated_inclusions_html,
    _client_output_warnings_for_payload,
    _compact_model_warnings,
    _get_journey_arc,
    _get_trip_glance,
    _merge_trip_glance,
    _normalise_journey_arc,
    _page_html_payload,
    _source_signature,
    build_visual_editor_payload,
)
from visual_editor_component.editor_result_applier import (
    _decode_visual_editor_result,
    _normalize_route_edit,
    _sanitize_editor_draft,
    _stable_output_edits_snapshot,
    apply_visual_editor_result,
)


def _try_apply_server_autosave(payload, output_edits, mark_dirty=None):
    """Compatibility wrapper for tests and older imports."""
    return try_apply_server_autosave(
        payload,
        output_edits,
        apply_visual_editor_result,
        mark_dirty=mark_dirty,
    )


def _payload_for_editor_render(parsed_rows, grouped_days, output_edits, mark_dirty=None):
    commit_nonce = st.session_state.get("_visual_editor_commit_nonce")
    if commit_nonce:
        return build_editor_commit_signal_payload(
            st.session_state.get("_visual_editor_current_source_signature")
        )

    with measure_timing(st.session_state, "build_editor_payload", count=len(parsed_rows or [])):
        payload = build_visual_editor_payload(parsed_rows, grouped_days, output_edits)
    st.session_state["_visual_editor_current_source_signature"] = str((payload.get("meta") or {}).get("source_signature") or "")
    st.session_state["latest_client_output_warnings"] = list(payload.get("client_output_warnings") or [])
    if _try_apply_server_autosave(payload, output_edits, mark_dirty=mark_dirty):
        with measure_timing(st.session_state, "build_editor_payload", count=len(parsed_rows or []), note="after_autosave"):
            payload = build_visual_editor_payload(parsed_rows, grouped_days, output_edits)
        st.session_state["_visual_editor_current_source_signature"] = str((payload.get("meta") or {}).get("source_signature") or "")
        st.session_state["latest_client_output_warnings"] = list(payload.get("client_output_warnings") or [])
    return payload


def render_visual_editor(parsed_rows, grouped_days, output_edits, rebuild_preview=None, mark_dirty=None):
    """Render and process the direct editable A4-page editor.

    Returns True only when a saved editor payload was applied. The app can then
    skip any additional rebuild based on the pre-save rows from the same rerun.
    """
    payload = _payload_for_editor_render(parsed_rows, grouped_days, output_edits, mark_dirty=mark_dirty)
    commit_nonce = st.session_state.get("_visual_editor_commit_nonce")
    result = render_visual_page_editor(payload, key="visual_page_editor", commit_nonce=commit_nonce)
    if result and result != st.session_state.get("_last_visual_editor_result"):
        st.session_state["_last_visual_editor_result"] = result
        with measure_timing(st.session_state, "apply_editor_changes"):
            applied_result = apply_visual_editor_result(result, output_edits, mark_dirty=mark_dirty)
        if applied_result:
            # Keep Save nearly instant: applying a compact editor delta must not
            # synchronously rebuild the full HTML/PDF render context on the same
            # Streamlit rerun.  The editor payload is rebuilt from output_edits
            # on the next render, while Add Pictures / PDF export explicitly
            # refresh the preview when they need committed server state.
            applied_nonce = st.session_state.get("_visual_editor_last_applied_commit_nonce")
            if applied_nonce and str(applied_nonce) == str(st.session_state.get(PDF_COMMIT_REQUEST_KEY, "")):
                st.session_state[PDF_COMMIT_READY_KEY] = True
            elif applied_nonce and str(applied_nonce) == str(st.session_state.get(ADD_PICTURES_COMMIT_REQUEST_KEY, "")):
                st.session_state[ADD_PICTURES_COMMIT_READY_KEY] = True
            if not st.session_state.get("_visual_editor_last_result_was_autosave"):
                refresh_active_saved_project_current_snapshot(st.session_state)
            if not applied_nonce:
                # Autosaves should feel invisible. Manual Save keeps the visible success message.
                if st.session_state.get("_visual_editor_last_result_changed") and not st.session_state.get("_visual_editor_last_result_was_autosave"):
                    st.success("Edits saved to preview and PDF export.")
            return True
    return False
