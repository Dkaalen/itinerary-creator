"""Render saved-project cloud and backup controls."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app_modules.project_file_download_cache import cached_project_file_payload
from app_modules.project_io import load_project_json
from app_modules.saved_project_file_action import PROJECT_FILE_MIME, prepare_saved_project_file_download
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_validation import SavedProjectError
from project_storage.project_browser import list_cloud_itineraries, load_latest_cloud_project_payload
from project_storage.runtime import project_storage_is_configured
from project_storage.workflow_hooks import save_project_payload_snapshot


@st.dialog("Open project")
def _render_open_project_dialog() -> None:
    """Render the saved-project browser/uploader in a modal workspace."""

    st.html(
        """
        <div class="open-project-copy">
          <strong>Open saved itinerary</strong>
          <span>Choose a cloud project, or upload a backup project file.</span>
        </div>
        """
    )
    if project_storage_is_configured():
        _render_cloud_project_browser()
    else:
        st.caption("Cloud project storage is not configured for this app session.")
    _render_backup_project_uploader()


def _render_cloud_project_browser() -> None:
    """Render cloud projects from Supabase."""

    try:
        projects = list_cloud_itineraries(limit=30)
    except Exception as error:
        st.warning("Could not read cloud projects from Supabase.")
        st.caption(str(error))
        return
    if not projects:
        st.caption("No cloud projects saved yet.")
        return
    st.html('<div class="cloud-project-list">')
    for project in projects:
        _render_cloud_project_card(project)
    st.html("</div>")


def _render_cloud_project_card(project: dict[str, Any]) -> None:
    project_id = str(project.get("id") or "")
    name = str(project.get("name") or "Untitled itinerary")
    updated = _short_time(project.get("updated_at") or project.get("created_at"))
    st.html(
        f"""
        <div class="cloud-project-card">
          <strong>{escape(name)}</strong>
          <span>{escape(updated)} · {escape(project_id[:8])}</span>
        </div>
        """
    )
    if st.button(f"Open {name}", key=f"open_cloud_project_{project_id}", use_container_width=True):
        _open_cloud_project(project_id)


def _open_cloud_project(project_id: str) -> None:
    payload = load_latest_cloud_project_payload(project_id)
    if not payload:
        st.warning("This cloud project has no saved itinerary snapshot yet.")
        return
    result = load_saved_project(st.session_state, payload)
    if result.ok:
        st.success(result.message or "Cloud project opened.")
        st.rerun()
    else:
        st.error(result.message or "Cloud project could not be opened.")


def _render_backup_project_uploader() -> None:
    uploaded_project = st.file_uploader(
        "Upload backup .itinerary.json file",
        type=["json"],
        key="open_project_file_upload",
    )
    if uploaded_project is None:
        return
    if st.button("Open uploaded backup", use_container_width=True):
        if load_project_json(uploaded_project, require_saved_project=True):
            st.rerun()


def render_open_project_file_action() -> None:
    """Render the top-bar saved-project open action."""

    if st.button("Open project", use_container_width=True, help="Open a saved cloud project or backup file."):
        _render_open_project_dialog()


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
        st.warning("Project was not saved to Supabase.")
        if st.session_state.get("project_storage_last_error"):
            st.caption(str(st.session_state.get("project_storage_last_error")))


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


def _short_time(value: object) -> str:
    text = str(value or "").replace("T", " ").replace("Z", " UTC")
    return text[:19] if text else "Saved project"
