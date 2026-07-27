"""Render the full-width saved-project explorer and backup opener."""

from __future__ import annotations

import streamlit as st

from app_modules.project_browser_detail_ui import render_selected_project_panel
from app_modules.project_browser_list_ui import render_project_table
from app_modules.project_browser_paging import PROJECT_PAGE_SIZE
from app_modules.project_browser_state import (
    browser_page_index,
    clear_delete_confirmation,
    clear_file_delete_confirmation,
    clear_open_candidate,
    clear_rename_candidate,
    remember_selected_project,
    selected_project_id,
    sync_project_query,
)
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_io import (
    cancel_pending_project_json_import,
    confirm_pending_project_json_import,
    pending_project_json_import,
    request_project_json_import,
)
from app_modules.session_state_keys import (
    OPEN_PROJECT_BROWSER_VISIBLE_KEY,
    OPEN_PROJECT_SEARCH_KEY,
    OPEN_PROJECT_SORT_KEY,
    PROJECT_STORAGE_BROWSER_SUCCESS_KEY,
    PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY,
)
from project_storage.errors import storage_user_message
from app_modules.project_storage_service import list_cloud_itinerary_page
from app_modules.project_storage_runtime import project_storage_is_configured

_SORT_OPTIONS = {
    "Recently modified": "recent",
    "Oldest modified": "oldest",
    "Name A–Z": "name",
    "Newest created": "created_recent",
    "Oldest created": "created_oldest",
}


def render_open_project_file_action() -> None:
    """Render only the compact toolbar action that opens Project Explorer."""

    if st.button("Open project", use_container_width=True, help="Open a saved cloud project or backup file."):
        st.session_state[OPEN_PROJECT_BROWSER_VISIBLE_KEY] = True


def render_open_project_workspace_if_visible() -> None:
    """Render Project Explorer at page width, outside the narrow toolbar columns."""

    if st.session_state.get(OPEN_PROJECT_BROWSER_VISIBLE_KEY):
        _render_open_project_workspace()


def _render_open_project_workspace() -> None:
    """Render the full-width project manager without stretching the page."""

    title_col, close_col = st.columns([0.84, 0.16], vertical_alignment="center")
    with title_col:
        st.html(
            """
            <div class="project-explorer-heading">
              <span class="project-explorer-folder">▰</span>
              <div>
                <strong>Project Explorer</strong>
                <span>Find, open, rename, duplicate, or remove a saved itinerary.</span>
              </div>
            </div>
            """
        )
    with close_col:
        if st.button("Close", key="close_open_project_browser", use_container_width=True):
            cancel_pending_project_json_import()
            st.session_state[OPEN_PROJECT_BROWSER_VISIBLE_KEY] = False
            st.rerun()
    if _render_pending_backup_confirmation():
        return
    if project_storage_is_configured():
        _render_cloud_project_browser()
    else:
        st.caption("Cloud project storage is not configured for this app session.")
    _render_backup_project_uploader()


def _render_cloud_project_browser() -> None:
    """Render one bounded server page as a selectable file-explorer workspace."""

    _render_browser_messages()
    with st.container(border=True, key="cloud_project_explorer"):
        search_col, sort_col = st.columns([0.68, 0.32], gap="small")
        with search_col:
            search = st.text_input(
                "Search projects",
                value=str(st.session_state.get(OPEN_PROJECT_SEARCH_KEY) or ""),
                key=OPEN_PROJECT_SEARCH_KEY,
                placeholder="Search by itinerary name…",
            )
        with sort_col:
            sort_label = st.selectbox("Sort", tuple(_SORT_OPTIONS), key=OPEN_PROJECT_SORT_KEY)
        sort_value = _SORT_OPTIONS.get(str(sort_label), "recent")
        sync_project_query(st.session_state, search=search, sort=sort_value)
        page_index = browser_page_index(st.session_state)
        try:
            page = list_cloud_itinerary_page(
                page_index=page_index,
                page_size=PROJECT_PAGE_SIZE,
                search=search,
                sort=sort_value,
            )
        except Exception:
            st.warning(storage_user_message("list"))
            return
        if not page.projects:
            if page.has_previous:
                from app_modules.project_browser_state import set_browser_page_index

                set_browser_page_index(st.session_state, page.page_index - 1)
                st.rerun()
            st.caption("No matching cloud projects." if search else "No cloud projects saved yet.")
            return

        selected = _selected_project(page.projects)
        active_id = active_project_id_from_state(st.session_state)
        list_col, detail_col = st.columns([0.66, 0.34], gap="large")
        with list_col:
            st.markdown("#### Saved projects")
            selected_id = render_project_table(
                page,
                selected_project_id=str(selected.get("id") or "") if selected else "",
                active_project_id=active_id,
                search=search,
                sort=sort_value,
            )
            if selected_id and (not selected or selected_id != str(selected.get("id") or "")):
                _select_project(selected_id)
                selected = next(
                    (project for project in page.projects if str(project.get("id") or "") == selected_id),
                    selected,
                )
        with detail_col:
            render_selected_project_panel(selected)


def _selected_project(projects: tuple[dict[str, object], ...]) -> dict[str, object] | None:
    selected_id = selected_project_id(st.session_state)
    selected = next((project for project in projects if str(project.get("id") or "") == selected_id), None)
    if selected:
        return selected
    active_id = active_project_id_from_state(st.session_state)
    selected = next((project for project in projects if str(project.get("id") or "") == active_id), projects[0])
    remember_selected_project(st.session_state, selected.get("id"))
    return selected


def _select_project(project_id: str) -> None:
    remember_selected_project(st.session_state, project_id)
    clear_open_candidate(st.session_state)
    clear_rename_candidate(st.session_state)
    clear_delete_confirmation(st.session_state)
    clear_file_delete_confirmation(st.session_state)


def _render_browser_messages() -> None:
    cleanup_warning = st.session_state.pop(PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY, "")
    if cleanup_warning:
        st.warning(str(cleanup_warning))
    success_message = st.session_state.pop(PROJECT_STORAGE_BROWSER_SUCCESS_KEY, "")
    if success_message:
        st.success(str(success_message))


def _render_backup_project_uploader() -> None:
    with st.expander("Open a backup file", expanded=False):
        st.caption("Use a .itinerary.json backup when the project is not available in cloud storage.")
        uploaded_project = st.file_uploader(
            "Upload backup .itinerary.json file",
            type=["json"],
            key="open_project_file_upload",
        )
        if uploaded_project is None:
            return
        if st.button("Open uploaded backup", use_container_width=True):
            opened = request_project_json_import(uploaded_project, require_saved_project=True)
            if opened is not False:
                st.rerun()


def _render_pending_backup_confirmation() -> bool:
    pending = pending_project_json_import()
    if pending is None:
        return False

    label = pending.filename or "itinerary backup"
    st.warning(f"Unsaved changes in the current workspace will be replaced when opening {label}.")
    keep_col, open_col = st.columns(2)
    with keep_col:
        if st.button("Keep current workspace", key="cancel_project_backup_import", use_container_width=True):
            cancel_pending_project_json_import()
            st.rerun()
            return True
    with open_col:
        if st.button("Open backup anyway", key="confirm_project_backup_import", use_container_width=True):
            if confirm_pending_project_json_import():
                st.rerun()
            return True
    return True
