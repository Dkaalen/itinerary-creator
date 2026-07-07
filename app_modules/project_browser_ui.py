"""Render the saved-project browser and backup opener."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app_modules.project_browser_calculation_files import render_calculation_files
from app_modules.project_browser_formatting import short_storage_time
from app_modules.project_browser_state import (
    clear_delete_confirmation,
    clear_file_delete_confirmation,
    delete_candidate_id,
    remember_delete_candidate,
)
from app_modules.project_delete_cleanup import clear_deleted_project_from_session
from app_modules.project_identity import set_active_project_id
from app_modules.project_io import load_project_json
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_validation import SavedProjectError
from project_storage.errors import storage_user_message
from project_storage.project_browser import (
    delete_cloud_itinerary_result,
    list_cloud_itineraries,
    load_latest_cloud_project_payload,
)
from project_storage.runtime import project_storage_is_configured


OPEN_PROJECT_BROWSER_VISIBLE_KEY = "open_project_browser_visible"


def _render_open_project_workspace() -> None:
    """Render the saved-project browser/uploader inline, without Streamlit fragments."""

    st.html(
        """
        <div class="open-project-workspace">
          <div class="open-project-copy">
            <strong>Open saved itinerary</strong>
            <span>Choose a cloud project, download saved calculator files, or upload a backup file.</span>
          </div>
        </div>
        """
    )
    close_col, _ = st.columns([0.22, 0.78])
    with close_col:
        if st.button("Close", key="close_open_project_browser", use_container_width=True):
            st.session_state[OPEN_PROJECT_BROWSER_VISIBLE_KEY] = False
            st.rerun()
    if project_storage_is_configured():
        _render_cloud_project_browser()
    else:
        st.caption("Cloud project storage is not configured for this app session.")
    _render_backup_project_uploader()


def render_open_project_file_action() -> None:
    """Render the top-bar saved-project open action and inline browser."""

    if st.button("Open project", use_container_width=True, help="Open a saved cloud project or backup file."):
        st.session_state[OPEN_PROJECT_BROWSER_VISIBLE_KEY] = True
    if st.session_state.get(OPEN_PROJECT_BROWSER_VISIBLE_KEY):
        _render_open_project_workspace()


def _render_cloud_project_browser() -> None:
    """Render cloud projects from Supabase."""

    cleanup_warning = st.session_state.pop("project_storage_delete_cleanup_warning", "")
    if cleanup_warning:
        st.warning(str(cleanup_warning))
    success_message = st.session_state.pop("project_storage_browser_success", "")
    if success_message:
        st.success(str(success_message))

    search = st.text_input(
        "Search projects",
        value=str(st.session_state.get("open_project_search") or ""),
        key="open_project_search",
        placeholder="Search by itinerary name…",
    )
    try:
        projects = list_cloud_itineraries(limit=50, search=search)
    except Exception:
        st.warning(storage_user_message("list"))
        return
    if not projects:
        st.caption("No matching cloud projects." if search else "No cloud projects saved yet.")
        return
    st.html('<div class="cloud-project-list">')
    for project in projects:
        _render_cloud_project_card(project)
    st.html("</div>")


def _render_cloud_project_card(project: dict[str, Any]) -> None:
    project_id = str(project.get("id") or "")
    if not project_id:
        return
    name = str(project.get("name") or "Untitled itinerary")
    updated = short_storage_time(project.get("updated_at") or project.get("created_at"))
    st.html(
        f"""
        <div class="cloud-project-card">
          <strong>{escape(name)}</strong>
          <span>Last saved {escape(updated)} · {escape(project_id[:8])}</span>
        </div>
        """
    )
    open_col, delete_col = st.columns([0.68, 0.32])
    with open_col:
        if st.button(f"Open {name}", key=f"open_cloud_project_{project_id}", use_container_width=True):
            _open_cloud_project(project_id)
    with delete_col:
        if st.button("Delete", key=f"delete_cloud_project_{project_id}", use_container_width=True):
            remember_delete_candidate(st.session_state, project_id=project_id, name=name)
            st.rerun()
    _render_delete_confirmation(project_id, name)
    render_calculation_files(project_id)


def _render_delete_confirmation(project_id: str, name: str) -> None:
    if delete_candidate_id(st.session_state) != project_id:
        return
    st.html(
        f"""
        <div class="cloud-project-delete-warning">
          <strong>Delete {escape(name)}?</strong>
          <span>This removes saved itinerary versions, calculator files, and PDFs.</span>
        </div>
        """
    )
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key=f"cancel_delete_cloud_project_{project_id}", use_container_width=True):
            clear_delete_confirmation(st.session_state)
            st.rerun()
    with confirm_col:
        if st.button("Delete permanently", key=f"confirm_delete_cloud_project_{project_id}", use_container_width=True):
            try:
                result = delete_cloud_itinerary_result(project_id)
                if result and result.ok:
                    clear_deleted_project_from_session(st.session_state, project_id)
                    clear_delete_confirmation(st.session_state)
                    if not result.storage_files_deleted:
                        st.session_state["project_storage_delete_cleanup_warning"] = (
                            "Project record was deleted, but one or more stored files could not be removed automatically."
                        )
                    st.session_state["project_storage_browser_success"] = f"Deleted {name}."
                    st.rerun()
                    return
                st.warning("Cloud storage is unavailable. Project was not deleted.")
            except Exception:
                st.error(storage_user_message("delete"))



def _open_cloud_project(project_id: str) -> None:
    try:
        payload = load_latest_cloud_project_payload(project_id)
    except Exception:
        st.error(storage_user_message("open"))
        return
    if not payload:
        st.warning("This cloud project has no saved itinerary snapshot yet.")
        return
    try:
        result = load_saved_project(st.session_state, payload, project_id_override=project_id)
    except SavedProjectError as error:
        st.error(f"Cloud project could not be opened: {error}")
        return
    except Exception:
        st.error(storage_user_message("open"))
        return
    if result.ok:
        set_active_project_id(st.session_state, project_id)
        clear_delete_confirmation(st.session_state)
        clear_file_delete_confirmation(st.session_state)
        st.session_state[OPEN_PROJECT_BROWSER_VISIBLE_KEY] = False
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
