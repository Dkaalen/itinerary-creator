"""Render saved-project save and backup-download actions."""

from __future__ import annotations

import streamlit as st

from app_modules.project_file_download_cache import cached_project_file_payload
from app_modules.project_save_rollback import capture_project_save_baseline, restore_project_save_baseline
from app_modules.saved_project_file_action import PROJECT_FILE_MIME, prepare_saved_project_file_download
from app_modules.saved_project_validation import SavedProjectError
from project_storage.errors import storage_user_message
from project_storage.runtime import project_storage_is_configured
from project_storage.workflow_hooks import save_project_payload_snapshot
from app_modules.session_state_keys import (
    ACTIVE_SAVED_PROJECT_ID_KEY,
    ITINERARY_NAME_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    PREVIEW_SIGNATURE_KEY,
    PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY,
    PROJECT_STORAGE_LAST_ERROR_KEY,
)
from app_modules.session_transitions import record_failed_save


def render_save_project_file_action(*, key_suffix: str = "current") -> None:
    """Render the user-facing saved-project action."""

    if not st.session_state.get(PARSED_ROWS_KEY) or not st.session_state.get(OUTPUT_EDITS_KEY):
        return
    if project_storage_is_configured():
        _render_cloud_save_project_action(key_suffix=key_suffix)
        return
    _render_backup_project_download(key_suffix=key_suffix)


def _render_cloud_save_project_action(*, key_suffix: str) -> None:
    if st.button("Save project", use_container_width=True, key=f"save_cloud_project_{key_suffix}"):
        baseline = capture_project_save_baseline(st.session_state)
        try:
            project_file = prepare_saved_project_file_download(st.session_state)
        except SavedProjectError as error:
            restore_project_save_baseline(st.session_state, baseline)
            st.warning(str(error))
            return
        if save_project_payload_snapshot(st.session_state, project_file.payload, source_type="manual_save"):
            st.success("Project saved to Supabase.")
            return
        message = str(st.session_state.get(PROJECT_STORAGE_LAST_ERROR_KEY) or storage_user_message("save"))
        detail = str(st.session_state.get(PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY) or "")
        record_failed_save(
            st.session_state,
            baseline=baseline,
            user_message=message,
            technical_detail=detail,
        )
        st.warning(message)


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
