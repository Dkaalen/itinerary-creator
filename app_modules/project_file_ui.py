"""Render saved-project file upload and download controls."""

from __future__ import annotations

import streamlit as st

from app_modules.project_io import load_project_json
from app_modules.saved_project_file_action import PROJECT_FILE_MIME, prepare_saved_project_file_download
from app_modules.saved_project_storage_ui import render_saved_project_storage_note
from app_modules.saved_project_validation import SavedProjectError


def render_open_project_file_action() -> None:
    """Render the user-facing saved-project upload action."""

    with st.container(border=True):
        st.markdown("**Open Project File**")
        render_saved_project_storage_note()
        uploaded_project = st.file_uploader(
            "Upload a saved .itinerary.json project file",
            type=["json"],
            key="open_project_file_upload",
            label_visibility="collapsed",
        )
        if uploaded_project is None:
            st.caption("Open a saved project without pasting supplier text again.")
            return
        if st.button("Open Project File", use_container_width=True):
            if load_project_json(uploaded_project, require_saved_project=True):
                st.rerun()


def render_save_project_file_action(*, key_suffix: str = "current") -> None:
    """Render the user-facing saved-project download action."""

    if not st.session_state.get("parsed_rows") or not st.session_state.get("output_edits"):
        return
    try:
        project_file = prepare_saved_project_file_download(st.session_state)
    except SavedProjectError as error:
        st.button("Save Project File", disabled=True, use_container_width=True, key=f"save_project_file_disabled_{key_suffix}")
        st.caption(str(error))
        return

    render_saved_project_storage_note()
    st.download_button(
        label="Save Project File",
        data=project_file.data,
        file_name=project_file.file_name,
        mime=PROJECT_FILE_MIME,
        use_container_width=True,
        key=f"save_project_file_{key_suffix}",
    )
