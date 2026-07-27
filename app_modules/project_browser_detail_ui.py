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
from app_modules.project_browser_bulk_ui import render_pending_project_action_confirmation
from app_modules.project_browser_calculation_files import render_calculation_files
from app_modules.project_browser_controls import ProjectBrowserQuery
from app_modules.project_browser_formatting import friendly_storage_time
from app_modules.project_browser_management_actions import apply_restore_from_trash
from app_modules.project_browser_state import (
    clear_open_candidate,
    clear_rename_candidate,
    open_candidate_id,
    remember_bulk_action,
    remember_rename_candidate,
    rename_candidate_id,
)
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_rename_state import apply_active_project_rename
from app_modules.project_storage_service import rename_cloud_project
from app_modules.session_state_keys import PROJECT_STORAGE_BROWSER_SUCCESS_KEY
from project_storage.errors import storage_user_message
from project_storage.project_metadata import project_owner_label


def render_selected_project_panel(
    project: dict[str, Any] | None,
    *,
    query: ProjectBrowserQuery | None = None,
) -> None:
    """Render metadata and actions for only the selected project."""

    query = query or ProjectBrowserQuery()
    st.markdown("#### Details")
    if not project:
        st.caption("Select a project row to view details and available actions.")
        return
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        st.caption("Select a valid project to continue.")
        return
    name = str(project.get("name") or "Untitled itinerary")
    is_active = active_project_id_from_state(st.session_state) == project_id
    _render_project_metadata(project, name=name, is_active=is_active, trash_only=query.trash_only)
    _render_project_actions(project_id, name, is_active=is_active, query=query)
    if render_pending_project_action_confirmation(query):
        return
    if not query.trash_only:
        _render_open_confirmation(project_id, name)
        _render_rename_form(project_id, name)
        render_calculation_files(project_id)


def _render_project_metadata(
    project: dict[str, Any],
    *,
    name: str,
    is_active: bool,
    trash_only: bool,
) -> None:
    owner = _owner_label(project.get("owner_slug"))
    folder = str(project.get("folder_name") or "No folder")
    saved = friendly_storage_time(
        project.get("last_saved_at") or project.get("updated_at") or project.get("created_at")
    )
    created = friendly_storage_time(project.get("created_at"))
    updated_by = _owner_label(project.get("updated_by"))
    revision = str(project.get("revision") or "—")
    deleted = friendly_storage_time(project.get("deleted_at")) if trash_only else ""
    active_badge = '<span class="cloud-project-active-badge">Open now</span>' if is_active else ""
    deleted_row = (
        f"<div><dt>Deleted</dt><dd>{escape(deleted)}</dd></div>" if trash_only else ""
    )
    st.html(
        f"""
        <div class="cloud-project-detail-card{' active' if is_active else ''}">
          <div class="cloud-project-detail-title">
            <strong title="{escape(name)}">{escape(name)}</strong>
            {active_badge}
          </div>
          <div class="cloud-project-path">{escape(owner)} / {escape(folder)}</div>
          <dl>
            <div><dt>Last saved</dt><dd>{escape(saved)}</dd></div>
            <div><dt>Saved by</dt><dd>{escape(updated_by)}</dd></div>
            <div><dt>Revision</dt><dd>{escape(revision)}</dd></div>
            <div><dt>Created</dt><dd>{escape(created)}</dd></div>
            {deleted_row}
          </dl>
        </div>
        """
    )


def _render_project_actions(
    project_id: str,
    name: str,
    *,
    is_active: bool,
    query: ProjectBrowserQuery,
) -> None:
    if query.trash_only:
        restore_col, delete_col = st.columns(2, gap="small")
        with restore_col:
            if st.button(
                "Restore project",
                key=f"restore_selected_cloud_project_{project_id}",
                use_container_width=True,
                type="primary",
            ):
                try:
                    apply_restore_from_trash(
                        st.session_state,
                        (project_id,),
                        actor_slug=query.actor_slug,
                    )
                except Exception:
                    st.error(storage_user_message("save"))
                else:
                    st.rerun()
        with delete_col:
            if st.button(
                "Delete permanently",
                key=f"purge_selected_cloud_project_{project_id}",
                use_container_width=True,
            ):
                remember_bulk_action(
                    st.session_state,
                    action="purge",
                    project_ids=(project_id,),
                    project_names=(name,),
                )
                st.rerun()
        return

    if st.button(
        "Project is open" if is_active else "Open project",
        key=f"open_selected_cloud_project_{project_id}",
        use_container_width=True,
        type="primary",
        disabled=is_active,
    ):
        request_open_cloud_project(project_id)
    rename_col, duplicate_col = st.columns(2, gap="small")
    with rename_col:
        if st.button(
            "Rename",
            key=f"rename_selected_cloud_project_{project_id}",
            use_container_width=True,
        ):
            clear_open_candidate(st.session_state)
            remember_rename_candidate(st.session_state, project_id)
            st.rerun()
    with duplicate_col:
        if st.button(
            "Save as copy",
            key=f"duplicate_selected_cloud_project_{project_id}",
            use_container_width=True,
        ):
            duplicate_cloud_project_action(project_id, name)
    if st.button(
        "Move to Trash",
        key=f"trash_selected_cloud_project_{project_id}",
        use_container_width=True,
    ):
        clear_open_candidate(st.session_state)
        clear_rename_candidate(st.session_state)
        remember_bulk_action(
            st.session_state,
            action="trash",
            project_ids=(project_id,),
            project_names=(name,),
        )
        st.rerun()


def _render_open_confirmation(project_id: str, name: str) -> None:
    if open_candidate_id(st.session_state) != project_id:
        return
    st.warning(f"Unsaved changes in the current workspace will be left behind when opening {name}.")
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button(
            "Keep current project",
            key=f"cancel_open_cloud_project_{project_id}",
            use_container_width=True,
        ):
            clear_open_candidate(st.session_state)
            st.rerun()
    with confirm_col:
        if st.button(
            "Open anyway",
            key=f"confirm_open_cloud_project_{project_id}",
            use_container_width=True,
        ):
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


def _owner_label(value: object) -> str:
    try:
        return project_owner_label(value or "unassigned")
    except ValueError:
        return "Unassigned"
