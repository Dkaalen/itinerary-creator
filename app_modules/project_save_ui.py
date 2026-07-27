"""Render saved-project save and backup-download actions."""

from __future__ import annotations

import streamlit as st

from app_modules.project_file_download_cache import cached_project_file_payload
from app_modules.project_persistence_state import active_cloud_project_is_persisted
from app_modules.project_save_as import normalize_project_name, prepare_project_save_as_payload
from app_modules.project_save_rollback import capture_project_save_baseline, restore_project_save_baseline
from app_modules.saved_project_file_action import PROJECT_FILE_MIME, prepare_saved_project_file_download
from app_modules.saved_project_validation import SavedProjectError
from project_storage.errors import storage_user_message
from app_modules.project_storage_runtime import project_storage_is_configured
from app_modules.project_storage_workflow import save_project_payload_snapshot
from app_modules.session_state_keys import (
    ACTIVE_SAVED_PROJECT_ID_KEY,
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    PREVIEW_SIGNATURE_KEY,
    PROJECT_SAVE_AS_NAME_KEY_PREFIX,
    PROJECT_SAVE_AS_VISIBLE_KEY,
    PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY,
    PROJECT_STORAGE_LAST_ERROR_KEY,
)
from app_modules.project_session_transitions import record_failed_save


def render_save_project_file_action(*, key_suffix: str = "current") -> None:
    """Render the user-facing saved-project action."""

    if not st.session_state.get(PARSED_ROWS_KEY) or not st.session_state.get(OUTPUT_EDITS_KEY):
        return
    if project_storage_is_configured():
        _render_cloud_save_project_action(key_suffix=key_suffix)
        return
    _render_backup_project_download(key_suffix=key_suffix)


def _render_cloud_save_project_action(*, key_suffix: str) -> None:
    with st.container(key="save_project_actions"):
        save_col, save_as_col = st.columns([0.62, 0.38], gap="small")
        with save_col:
            save_label = "Save" if active_cloud_project_is_persisted(st.session_state) else "Save project"
            save_clicked = st.button(save_label, use_container_width=True, key=f"save_cloud_project_{key_suffix}")
        with save_as_col:
            save_as_clicked = st.button("Save as", use_container_width=True, key=f"save_as_cloud_project_{key_suffix}")

    if save_clicked:
        _save_current_cloud_project()
        return
    if save_as_clicked:
        st.session_state[PROJECT_SAVE_AS_VISIBLE_KEY] = True
        st.rerun()
        return
    if st.session_state.get(PROJECT_SAVE_AS_VISIBLE_KEY):
        _render_save_as_form(key_suffix=key_suffix)


def _save_current_cloud_project() -> None:
    baseline = capture_project_save_baseline(st.session_state)
    try:
        project_name = normalize_project_name(
            st.session_state.get(ITINERARY_NAME_INPUT_KEY)
            or st.session_state.get(ITINERARY_NAME_KEY)
        )
        st.session_state[ITINERARY_NAME_KEY] = project_name
        st.session_state[ITINERARY_NAME_INPUT_KEY] = project_name
        project_file = prepare_saved_project_file_download(st.session_state)
    except (SavedProjectError, ValueError) as error:
        restore_project_save_baseline(st.session_state, baseline)
        st.warning(str(error))
        return
    if save_project_payload_snapshot(st.session_state, project_file.payload, source_type="manual_save"):
        st.success("Project saved to Supabase.")
        return
    _report_failed_save(baseline)


def _render_save_as_form(*, key_suffix: str) -> None:
    current_name = str(
        st.session_state.get(ITINERARY_NAME_INPUT_KEY)
        or st.session_state.get(ITINERARY_NAME_KEY)
        or "Untitled itinerary"
    ).strip()
    name_key = f"{PROJECT_SAVE_AS_NAME_KEY_PREFIX}{key_suffix}"
    with st.form(f"save_as_cloud_project_form_{key_suffix}"):
        new_name = st.text_input(
            "New project name",
            value=f"{current_name} — Copy",
            max_chars=160,
            key=name_key,
        )
        with st.container(key="save_as_project_actions"):
            save_col, cancel_col = st.columns([0.66, 0.34], gap="small")
            with save_col:
                save = st.form_submit_button("Save as new project", use_container_width=True)
            with cancel_col:
                cancel = st.form_submit_button("Cancel", use_container_width=True)
    if cancel:
        _clear_save_as_state(key_suffix=key_suffix)
        st.rerun()
        return
    if not save:
        return

    baseline = capture_project_save_baseline(st.session_state)
    try:
        current = prepare_saved_project_file_download(st.session_state)
        payload = prepare_project_save_as_payload(current.payload, new_name=new_name)
    except (SavedProjectError, ValueError) as error:
        restore_project_save_baseline(st.session_state, baseline)
        st.warning(str(error))
        return

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    new_id = str(metadata.get("project_id") or "")
    if save_project_payload_snapshot(
        st.session_state,
        payload,
        source_type="save_as",
        project_id_override=new_id,
        project_was_persisted=False,
    ):
        _clear_save_as_state(key_suffix=key_suffix)
        st.success("New project saved to Supabase.")
        return
    _report_failed_save(baseline)


def _report_failed_save(baseline: dict[str, object]) -> None:
    message = str(st.session_state.get(PROJECT_STORAGE_LAST_ERROR_KEY) or storage_user_message("save"))
    detail = str(st.session_state.get(PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY) or "")
    record_failed_save(
        st.session_state,
        baseline=baseline,
        user_message=message,
        technical_detail=detail,
    )
    st.warning(message)


def _clear_save_as_state(*, key_suffix: str) -> None:
    st.session_state.pop(PROJECT_SAVE_AS_VISIBLE_KEY, None)
    st.session_state.pop(f"{PROJECT_SAVE_AS_NAME_KEY_PREFIX}{key_suffix}", None)


def _render_backup_project_download(*, key_suffix: str) -> None:
    try:
        signature = ":".join([
            str(st.session_state.get(PREVIEW_SIGNATURE_KEY) or ""),
            str(st.session_state.get(ACTIVE_SAVED_PROJECT_ID_KEY) or ""),
            str(st.session_state.get(ITINERARY_NAME_KEY) or ""),
        ])
        project_file = cached_project_file_payload(
            st.session_state,
            signature,
            lambda: prepare_saved_project_file_download(st.session_state),
        )
    except SavedProjectError as error:
        st.button("Download backup file", disabled=True, use_container_width=True, key=f"save_project_file_disabled_{key_suffix}")
        st.caption(str(error))
        return

    st.download_button(
        label="Download backup file",
        data=project_file.data,
        file_name=project_file.file_name,
        mime=PROJECT_FILE_MIME,
        use_container_width=True,
        key=f"save_project_file_{key_suffix}",
    )
