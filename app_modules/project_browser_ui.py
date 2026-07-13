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
    clear_open_candidate,
    clear_rename_candidate,
    delete_candidate_id,
    open_candidate_id,
    remember_delete_candidate,
    remember_open_candidate,
    remember_rename_candidate,
    rename_candidate_id,
)
from app_modules.project_delete_cleanup import clear_deleted_project_from_session
from app_modules.project_identity import active_project_id_from_state, set_active_project_id
from app_modules.project_io import load_project_json
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_validation import SavedProjectError
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.project_rename_state import apply_active_project_rename
from project_storage.errors import storage_user_message
from project_storage.project_browser import (
    delete_cloud_itinerary_result,
    list_cloud_itineraries,
    load_latest_cloud_project_payload,
)
from project_storage.runtime import project_storage_is_configured
from project_storage.project_management import duplicate_cloud_project, rename_cloud_project


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
    is_active = active_project_id_from_state(st.session_state) == project_id
    active_label = " · Active project" if is_active else ""
    st.html(
        f"""
        <div class="cloud-project-card{' active' if is_active else ''}">
          <strong>{escape(name)}</strong>
          <span>Last saved {escape(updated)} · {escape(project_id[:8])}{escape(active_label)}</span>
        </div>
        """
    )
    open_col, rename_col, duplicate_col, delete_col = st.columns([0.38, 0.22, 0.22, 0.18])
    with open_col:
        if st.button("Open", key=f"open_cloud_project_{project_id}", use_container_width=True, disabled=is_active):
            _request_open_cloud_project(project_id)
    with rename_col:
        if st.button("Rename", key=f"rename_cloud_project_{project_id}", use_container_width=True):
            remember_rename_candidate(st.session_state, project_id)
            st.rerun()
    with duplicate_col:
        if st.button("Duplicate", key=f"duplicate_cloud_project_{project_id}", use_container_width=True):
            _duplicate_cloud_project(project_id, name)
    with delete_col:
        if st.button("Delete", key=f"delete_cloud_project_{project_id}", use_container_width=True):
            remember_delete_candidate(st.session_state, project_id=project_id, name=name)
            st.rerun()
    _render_open_confirmation(project_id, name)
    _render_rename_form(project_id, name)
    _render_delete_confirmation(project_id, name)
    render_calculation_files(project_id)


def _request_open_cloud_project(project_id: str) -> None:
    active_id = active_project_id_from_state(st.session_state)
    if active_id and active_id != project_id and active_project_has_unsaved_changes(st.session_state):
        remember_open_candidate(st.session_state, project_id)
        st.rerun()
        return
    _open_cloud_project(project_id)


def _render_open_confirmation(project_id: str, name: str) -> None:
    if open_candidate_id(st.session_state) != project_id:
        return
    st.warning(f"Unsaved changes in the active project will be left behind when opening {name}.")
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("Keep current project", key=f"cancel_open_cloud_project_{project_id}", use_container_width=True):
            clear_open_candidate(st.session_state)
            st.rerun()
    with confirm_col:
        if st.button("Open anyway", key=f"confirm_open_cloud_project_{project_id}", use_container_width=True):
            clear_open_candidate(st.session_state)
            _open_cloud_project(project_id)


def _render_rename_form(project_id: str, name: str) -> None:
    if rename_candidate_id(st.session_state) != project_id:
        return
    with st.form(f"rename_cloud_project_form_{project_id}"):
        new_name = st.text_input("Project name", value=name, max_chars=160)
        save_col, cancel_col = st.columns(2)
        with save_col:
            save = st.form_submit_button("Save name", use_container_width=True)
        with cancel_col:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
    if cancel:
        clear_rename_candidate(st.session_state)
        st.rerun()
    if not save:
        return
    try:
        result = rename_cloud_project(project_id, new_name)
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error(storage_user_message("save"))
        return
    if not result:
        st.warning("Cloud storage is unavailable. Project was not renamed.")
        return
    if active_project_id_from_state(st.session_state) == project_id:
        apply_active_project_rename(st.session_state, result)
    clear_rename_candidate(st.session_state)
    st.session_state["project_storage_browser_success"] = f"Renamed project to {result['name']}."
    st.rerun()


def _duplicate_cloud_project(project_id: str, name: str) -> None:
    try:
        result = duplicate_cloud_project(project_id, f"{name} — Copy")
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error(storage_user_message("save"))
        return
    if not result:
        st.warning("Cloud storage is unavailable. Project was not duplicated.")
        return
    st.session_state["project_storage_browser_success"] = f"Created {result['name']}."
    st.rerun()


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
        clear_open_candidate(st.session_state)
        clear_rename_candidate(st.session_state)
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
