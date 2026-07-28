"""Bulk-management controls for selected Project Explorer projects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from html import escape

import streamlit as st

from app_modules.performance_telemetry import record_trace, telemetry_is_active
from app_modules.project_browser_controls import ProjectBrowserQuery
from app_modules.project_browser_management_actions import (
    apply_delete_projects,
    apply_folder_change,
    apply_owner_change,
)
from app_modules.project_browser_paging import ProjectPage
from app_modules.project_browser_state import (
    clear_bulk_action,
    consume_bulk_action,
    pending_bulk_action,
    project_action_token_fingerprint,
    project_table_revision,
    remember_bulk_action,
)
from app_modules.session_state_keys import PROJECT_STORAGE_BROWSER_WARNING_KEY
from project_storage.errors import storage_user_message
from project_storage.project_metadata import PROJECT_OWNER_LABELS, PROJECT_OWNER_SLUGS


def render_bulk_management_panel(
    page: ProjectPage,
    *,
    selected_ids: tuple[str, ...],
    selected_projects: Sequence[Mapping[str, object]] = (),
    query: ProjectBrowserQuery,
) -> None:
    """Render one action row for an exact durable-ID selection."""

    del page
    project_ids = tuple(dict.fromkeys(str(value or "").strip() for value in selected_ids if str(value or "").strip()))
    if not project_ids:
        return
    names_by_id = {
        str(project.get("id") or "").strip(): str(project.get("name") or "Untitled itinerary")
        for project in selected_projects
        if str(project.get("id") or "").strip()
    }
    project_names = tuple(names_by_id.get(project_id, "Untitled itinerary") for project_id in project_ids)
    if render_pending_project_action_confirmation(query):
        return

    st.html(
        f'<div class="cloud-project-selection-summary"><strong>{len(project_ids)} projects selected</strong>'
        '<span>Choose one action for this exact selection.</span></div>'
    )
    with st.container(key="project_explorer_bulk_actions"):
        action_col, value_col, apply_col = st.columns([0.25, 0.51, 0.24], gap="small", vertical_alignment="bottom")
        with action_col:
            action = st.selectbox(
                "Action",
                _bulk_action_options(query),
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
                if telemetry_is_active(st.session_state):
                    record_trace(
                        st.session_state,
                        "project_delete_requested",
                        project_ids=project_ids,
                        project_count=len(project_ids),
                        list_revision=project_table_revision(st.session_state),
                    )
                remember_bulk_action(
                    st.session_state,
                    action="delete",
                    project_ids=project_ids,
                    project_names=project_names,
                )
                st.rerun()


def _bulk_action_options(query: ProjectBrowserQuery) -> tuple[str, ...]:
    if not query.organization_available:
        return ("delete",)
    return ("owner", "folder", "delete")


def render_pending_project_action_confirmation(query: ProjectBrowserQuery | None = None) -> bool:
    """Render and validate one exact, one-use direct-delete confirmation."""

    del query
    pending = pending_bulk_action(st.session_state)
    if pending.action != "delete" or not pending.project_ids or not pending.token:
        return False
    count = len(pending.project_ids)
    preview = ", ".join(pending.project_names[:3])
    if len(pending.project_names) > 3:
        preview = f"{preview}, and {len(pending.project_names) - 3} more"
    with st.container(key="project_explorer_delete_confirmation"):
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
            if st.button(
                "Cancel",
                key=f"cancel_bulk_project_action_{pending.token}",
                use_container_width=True,
            ):
                if telemetry_is_active(st.session_state):
                    record_trace(
                        st.session_state,
                        "project_delete_cancelled",
                        project_ids=pending.project_ids,
                        confirmation_token_id=project_action_token_fingerprint(pending.token),
                    )
                clear_bulk_action(st.session_state)
                st.rerun()
        with confirm_col:
            if st.button(
                "Delete permanently",
                key=f"confirm_bulk_project_action_{pending.token}",
                use_container_width=True,
            ):
                consumed = consume_bulk_action(
                    st.session_state,
                    token=pending.token,
                    project_ids=pending.project_ids,
                    list_revision=pending.list_revision,
                )
                if consumed is None:
                    clear_bulk_action(st.session_state)
                    st.session_state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = (
                        "That delete confirmation is no longer current. Review the selection and try again."
                    )
                    st.rerun()
                    return True
                if telemetry_is_active(st.session_state):
                    record_trace(
                        st.session_state,
                        "project_delete_confirmed",
                        project_ids=consumed.project_ids,
                        project_count=len(consumed.project_ids),
                        confirmation_token=consumed.token,
                        list_revision=consumed.list_revision,
                    )
                try:
                    apply_delete_projects(
                        st.session_state,
                        consumed.project_ids,
                        confirmation_token=consumed.token,
                    )
                except Exception:
                    st.error(storage_user_message("delete"))
                else:
                    st.rerun()
    return True


__all__ = [
    "_bulk_action_options",
    "render_bulk_management_panel",
    "render_pending_project_action_confirmation",
]
