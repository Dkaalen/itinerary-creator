"""Selected-project details and actions for Project Explorer."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app_modules.project_browser_actions import (
    duplicate_cloud_project_action,
    open_cloud_project,
    request_open_cloud_project,
)
from app_modules.project_browser_calculation_files import render_calculation_files
from app_modules.project_browser_formatting import short_storage_time
from app_modules.project_browser_state import (
    clear_delete_confirmation,
    clear_open_candidate,
    clear_rename_candidate,
    delete_candidate_id,
    open_candidate_id,
    remember_delete_candidate,
    remember_rename_candidate,
    rename_candidate_id,
)
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_rename_state import apply_active_project_rename
from app_modules.session_state_keys import PROJECT_STORAGE_BROWSER_SUCCESS_KEY
from app_modules.project_session_transitions import complete_project_delete
from project_storage.errors import storage_user_message
from app_modules.project_storage_service import delete_cloud_itinerary_result, rename_cloud_project


def render_selected_project_panel(project: dict[str, Any] | None) -> None:
    """Render metadata and actions for only the selected project."""

    st.markdown("#### Details")
    if not project:
        st.caption("Select a project row to view details and available actions.")
        return
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        st.caption("Select a valid project to continue.")
        return
    name = str(project.get("name") or "Untitled itinerary")
    status = str(project.get("status") or "draft").replace("_", " ").title()
    updated = short_storage_time(project.get("updated_at") or project.get("created_at"))
    created = short_storage_time(project.get("created_at"))
    is_active = active_project_id_from_state(st.session_state) == project_id
    st.html(
        f"""
        <div class="cloud-project-detail-card{' active' if is_active else ''}">
          <strong>{escape(name)}</strong>
          <dl>
            <div><dt>Status</dt><dd>{escape(status)}{' · Active' if is_active else ''}</dd></div>
            <div><dt>Modified</dt><dd>{escape(updated)}</dd></div>
            <div><dt>Created</dt><dd>{escape(created)}</dd></div>
            <div><dt>Project ID</dt><dd>{escape(project_id[:8])}</dd></div>
          </dl>
        </div>
        """
    )
    _render_project_actions(project_id, name, is_active=is_active)
    _render_open_confirmation(project_id, name)
    _render_rename_form(project_id, name)
    _render_delete_confirmation(project_id, name)
    render_calculation_files(project_id)


def _render_project_actions(project_id: str, name: str, *, is_active: bool) -> None:
    open_col, rename_col, duplicate_col, delete_col = st.columns([1.35, 1, 1, 1], gap="small")
    with open_col:
        if st.button(
            "Active" if is_active else "Open",
            key=f"open_selected_cloud_project_{project_id}",
            use_container_width=True,
            type="primary",
            disabled=is_active,
        ):
            request_open_cloud_project(project_id)
    with rename_col:
        if st.button("Rename", key=f"rename_selected_cloud_project_{project_id}", use_container_width=True):
            clear_open_candidate(st.session_state)
            clear_delete_confirmation(st.session_state)
            remember_rename_candidate(st.session_state, project_id)
            st.rerun()
    with duplicate_col:
        if st.button("Duplicate", key=f"duplicate_selected_cloud_project_{project_id}", use_container_width=True):
            duplicate_cloud_project_action(project_id, name)
    with delete_col:
        if st.button("Delete", key=f"delete_selected_cloud_project_{project_id}", use_container_width=True):
            clear_open_candidate(st.session_state)
            clear_rename_candidate(st.session_state)
            remember_delete_candidate(st.session_state, project_id=project_id, name=name)
            st.rerun()


def _render_open_confirmation(project_id: str, name: str) -> None:
    if open_candidate_id(st.session_state) != project_id:
        return
    st.warning(f"Unsaved changes in the current workspace will be left behind when opening {name}.")
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("Keep current project", key=f"cancel_open_cloud_project_{project_id}", use_container_width=True):
            clear_open_candidate(st.session_state)
            st.rerun()
    with confirm_col:
        if st.button("Open anyway", key=f"confirm_open_cloud_project_{project_id}", use_container_width=True):
            clear_open_candidate(st.session_state)
            open_cloud_project(project_id)


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
    st.session_state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] = f"Renamed project to {result['name']}."
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
                    complete_project_delete(
                        st.session_state,
                        project_id=project_id,
                        name=name,
                        storage_files_deleted=result.storage_files_deleted,
                    )
                    st.rerun()
                    return
                st.warning("Cloud storage is unavailable. Project was not deleted.")
            except Exception:
                st.error(storage_user_message("delete"))
