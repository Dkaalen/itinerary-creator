"""Render saved-project save and backup-download actions."""

from __future__ import annotations

import streamlit as st

from app_modules.project_file_download_cache import cached_project_file_payload
from app_modules.saved_project_file_action import PROJECT_FILE_MIME, prepare_saved_project_file_download
from app_modules.saved_project_validation import SavedProjectError
from project_storage.errors import storage_user_message
from project_storage.runtime import project_storage_is_configured
from project_storage.workflow_hooks import save_project_payload_snapshot


def render_save_project_file_action(*, key_suffix: str = "current") -> None:
    """Render the user-facing saved-project action."""

    if not st.session_state.get("parsed_rows") or not st.session_state.get("output_edits"):
        return
    if project_storage_is_configured():
        _render_cloud_save_project_action(key_suffix=key_suffix)
        return
    _render_backup_project_download(key_suffix=key_suffix)


def _render_cloud_save_project_action(*, key_suffix: str) -> None:
    if st.button("Save project", use_container_width=True, key=f"save_cloud_project_{key_suffix}"):
        try:
            project_file = prepare_saved_project_file_download(st.session_state)
        except SavedProjectError as error:
            st.warning(str(error))
            return
        if save_project_payload_snapshot(st.session_state, project_file.payload, source_type="manual_save"):
            st.success("Project saved to Supabase.")
            return
        st.warning(str(st.session_state.get("project_storage_last_error") or storage_user_message("save")))


def _render_backup_project_download(*, key_suffix: str) -> None:
    try:
        signature = ":".join([
            str(st.session_state.get("preview_signature") or ""),
            str(st.session_state.get("active_saved_project_id") or ""),
            str(st.session_state.get("itinerary_name") or ""),
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
