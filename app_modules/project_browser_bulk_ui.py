"""Bulk-management controls for selected Project Explorer rows."""

from __future__ import annotations

from html import escape

import streamlit as st

from app_modules.project_browser_controls import ProjectBrowserQuery
from app_modules.project_browser_management_actions import (
    apply_delete_projects,
    apply_folder_change,
    apply_owner_change,
)
from app_modules.project_browser_paging import ProjectPage
from app_modules.project_browser_state import bulk_action, clear_bulk_action, remember_bulk_action
from project_storage.errors import storage_user_message
from project_storage.project_metadata import PROJECT_OWNER_LABELS, PROJECT_OWNER_SLUGS


def render_bulk_management_panel(
    page: ProjectPage,
    *,
    selected_ids: tuple[str, ...],
    query: ProjectBrowserQuery,
) -> None:
    """Render one compact action row for several selected projects."""

    selected_set = set(selected_ids)
    projects = tuple(
        project
        for project in page.projects
        if str(project.get("id") or "").strip() in selected_set
    )
    if not projects:
        return
    if render_pending_project_action_confirmation(query):
        return

    project_ids = tuple(str(project.get("id") or "").strip() for project in projects)
    project_names = tuple(str(project.get("name") or "Untitled itinerary") for project in projects)
    st.html(
        f'<div class="cloud-project-selection-summary"><strong>{len(project_ids)} projects selected</strong>'
        '<span>Choose one action for this selection.</span></div>'
    )
    action_col, value_col, apply_col = st.columns([0.25, 0.51, 0.24], gap="small", vertical_alignment="bottom")
    with action_col:
        action = st.selectbox(
            "Action",
            ("owner", "folder", "delete"),
            format_func=lambda value: {
                "owner": "Change owner",
                "folder": "Move to folder/reference",
                "delete": "Delete projects",
            }[value],
            key="bulk_project_action_choice",
        )
    if action == "owner":
        with value_col:
            owner_slug = st.selectbox(
                "New owner",
                PROJECT_OWNER_SLUGS,
                format_func=lambda value: PROJECT_OWNER_LABELS[value],
                key="bulk_project_owner_value",
            )
        with apply_col:
            apply_clicked = st.button("Apply", key="bulk_apply_owner", type="primary", use_container_width=True)
        if apply_clicked:
            try:
                apply_owner_change(
                    st.session_state,
                    project_ids,
                    owner_slug=str(owner_slug),
                    actor_slug=query.actor_slug,
                )
            except (ValueError, Exception) as error:
                st.error(str(error) if isinstance(error, ValueError) else storage_user_message("save"))
            else:
                st.rerun()
        return
    if action == "folder":
        with value_col:
            folder_name = st.text_input(
                "Folder/reference",
                key="bulk_project_folder_value",
                max_chars=80,
                placeholder="ITIN-2020 (leave blank to clear)",
            )
        with apply_col:
            apply_clicked = st.button("Apply", key="bulk_apply_folder", type="primary", use_container_width=True)
        if apply_clicked:
            try:
                apply_folder_change(
                    st.session_state,
                    project_ids,
                    folder_name=str(folder_name or ""),
                    actor_slug=query.actor_slug,
                )
            except (ValueError, Exception) as error:
                st.error(str(error) if isinstance(error, ValueError) else storage_user_message("save"))
            else:
                st.rerun()
        return

    with value_col:
        st.caption("Permanently remove the selected projects and their saved files.")
    with apply_col:
        if st.button(
            f"Delete {len(project_ids)}",
            key="bulk_delete_projects",
            use_container_width=True,
        ):
            remember_bulk_action(
                st.session_state,
                action="delete",
                project_ids=project_ids,
                project_names=project_names,
            )
            st.rerun()


def render_pending_project_action_confirmation(query: ProjectBrowserQuery | None = None) -> bool:
    """Render a pending direct-delete confirmation."""

    del query
    action, project_ids, project_names = bulk_action(st.session_state)
    if action != "delete" or not project_ids:
        return False
    count = len(project_ids)
    preview = ", ".join(project_names[:3])
    if len(project_names) > 3:
        preview = f"{preview}, and {len(project_names) - 3} more"
    st.html(
        f"""
        <div class="cloud-project-delete-warning">
          <strong>{escape(f'Delete {count} project' + ('s' if count != 1 else '') + '?')}</strong>
          <span>This permanently removes saved versions, Calculator files and PDFs.</span>
          <small>{escape(preview)}</small>
        </div>
        """
    )
    cancel_col, confirm_col = st.columns(2, gap="small")
    with cancel_col:
        if st.button("Cancel", key="cancel_bulk_project_action", use_container_width=True):
            clear_bulk_action(st.session_state)
            st.rerun()
    with confirm_col:
        if st.button("Delete permanently", key="confirm_bulk_project_action", use_container_width=True):
            try:
                apply_delete_projects(st.session_state, project_ids)
            except Exception:
                st.error(storage_user_message("delete"))
            else:
                st.rerun()
    return True
