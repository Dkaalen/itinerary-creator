"""Bulk-management controls for selected Project Explorer rows."""

from __future__ import annotations

from html import escape

import streamlit as st

from app_modules.project_browser_controls import ProjectBrowserQuery
from app_modules.project_browser_management_actions import (
    apply_folder_change,
    apply_move_to_trash,
    apply_owner_change,
    apply_permanent_purge,
    apply_restore_from_trash,
)
from app_modules.project_browser_paging import ProjectPage
from app_modules.project_browser_state import (
    bulk_action,
    clear_bulk_action,
    remember_bulk_action,
)
from project_storage.errors import storage_user_message
from project_storage.project_metadata import PROJECT_OWNER_LABELS, PROJECT_OWNER_SLUGS


def render_bulk_management_panel(
    page: ProjectPage,
    *,
    selected_ids: tuple[str, ...],
    query: ProjectBrowserQuery,
) -> None:
    """Render compact multi-project actions for the current page selection."""

    selected_projects = tuple(
        project for project in page.projects if str(project.get("id") or "").strip() in set(selected_ids)
    )
    st.html(
        f"""
        <div class="cloud-project-manage-summary">
          <strong>Manage projects</strong>
          <span>{len(selected_projects)} selected on this page</span>
        </div>
        """
    )
    if render_pending_project_action_confirmation(query):
        return
    if not selected_projects:
        st.caption("Select one or more rows in the table to show bulk actions.")
        return

    project_ids = tuple(str(project.get("id") or "").strip() for project in selected_projects)
    project_names = tuple(str(project.get("name") or "Untitled itinerary") for project in selected_projects)
    if query.trash_only:
        _render_trash_actions(project_ids, project_names, query=query)
    else:
        _render_organization_actions(project_ids, project_names=project_names, query=query)


def render_pending_project_action_confirmation(query: ProjectBrowserQuery) -> bool:
    """Render a pending single- or multi-project destructive confirmation."""

    pending_action, pending_ids, pending_names = bulk_action(st.session_state)
    if not pending_action or not pending_ids:
        return False
    _render_destructive_confirmation(
        action=pending_action,
        project_ids=pending_ids,
        project_names=pending_names,
        query=query,
    )
    return True


def _render_organization_actions(
    project_ids: tuple[str, ...],
    *,
    project_names: tuple[str, ...],
    query: ProjectBrowserQuery,
) -> None:
    action = st.selectbox(
        "Bulk action",
        ("owner", "folder", "trash"),
        format_func=lambda value: {
            "owner": "Change owner",
            "folder": "Move to folder/reference",
            "trash": "Move to Trash",
        }[value],
        key="bulk_project_action_choice",
    )
    if action == "owner":
        with st.form("bulk_project_owner_form", border=False):
            owner_slug = st.selectbox(
                "New owner",
                PROJECT_OWNER_SLUGS,
                format_func=lambda value: PROJECT_OWNER_LABELS[value],
                key="bulk_project_owner_value",
            )
            update_owner = st.form_submit_button("Apply to selected", use_container_width=True, type="primary")
        if update_owner:
            try:
                apply_owner_change(
                    st.session_state,
                    project_ids,
                    owner_slug=str(owner_slug),
                    actor_slug=query.actor_slug,
                )
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error(storage_user_message("save"))
            else:
                st.rerun()
        return
    if action == "folder":
        with st.form("bulk_project_folder_form", border=False):
            folder_name = st.text_input(
                "Folder/reference",
                key="bulk_project_folder_value",
                max_chars=80,
                placeholder="ITIN-2020 (leave blank to clear)",
            )
            update_folder = st.form_submit_button("Apply to selected", use_container_width=True, type="primary")
        if update_folder:
            try:
                apply_folder_change(
                    st.session_state,
                    project_ids,
                    folder_name=str(folder_name or ""),
                    actor_slug=query.actor_slug,
                )
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error(storage_user_message("save"))
            else:
                st.rerun()
        return
    _render_move_to_trash_action(project_ids, project_names)

def _render_move_to_trash_action(project_ids: tuple[str, ...], project_names: tuple[str, ...]) -> None:
    if st.button(
        f"Move {len(project_ids)} selected to Trash",
        key="bulk_move_projects_to_trash",
        use_container_width=True,
    ):
        remember_bulk_action(
            st.session_state,
            action="trash",
            project_ids=project_ids,
            project_names=project_names,
        )
        st.rerun()


def _render_trash_actions(
    project_ids: tuple[str, ...],
    project_names: tuple[str, ...],
    *,
    query: ProjectBrowserQuery,
) -> None:
    restore_col, delete_col = st.columns(2, gap="small")
    with restore_col:
        if st.button(
            f"Restore {len(project_ids)} selected",
            key="bulk_restore_projects",
            use_container_width=True,
            type="primary",
        ):
            try:
                apply_restore_from_trash(
                    st.session_state,
                    project_ids,
                    actor_slug=query.actor_slug,
                )
            except Exception:
                st.error(storage_user_message("save"))
            else:
                st.rerun()
    with delete_col:
        if st.button(
            f"Delete {len(project_ids)} permanently",
            key="bulk_permanently_delete_projects",
            use_container_width=True,
        ):
            remember_bulk_action(
                st.session_state,
                action="purge",
                project_ids=project_ids,
                project_names=project_names,
            )
            st.rerun()


def _render_destructive_confirmation(
    *,
    action: str,
    project_ids: tuple[str, ...],
    project_names: tuple[str, ...],
    query: ProjectBrowserQuery,
) -> None:
    count = len(project_ids)
    preview = ", ".join(project_names[:3])
    if len(project_names) > 3:
        preview = f"{preview}, and {len(project_names) - 3} more"
    if action == "purge":
        title = f"Permanently delete {count} project{'s' if count != 1 else ''}?"
        explanation = "This removes saved versions, Calculator files and PDFs. It cannot be undone."
        confirm_label = "Delete permanently"
    else:
        title = f"Move {count} project{'s' if count != 1 else ''} to Trash?"
        explanation = "Projects can be restored later from the Trash view."
        confirm_label = "Move to Trash"
    st.html(
        f"""
        <div class="cloud-project-delete-warning">
          <strong>{escape(title)}</strong>
          <span>{escape(explanation)}</span>
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
        if st.button(confirm_label, key="confirm_bulk_project_action", use_container_width=True):
            try:
                if action == "purge":
                    apply_permanent_purge(st.session_state, project_ids)
                else:
                    apply_move_to_trash(
                        st.session_state,
                        project_ids,
                        actor_slug=query.actor_slug,
                    )
            except Exception:
                st.error(storage_user_message("delete"))
            else:
                st.rerun()
