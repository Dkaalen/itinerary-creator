"""Render the full-width saved-project explorer and backup opener."""

from __future__ import annotations

import streamlit as st

from app_modules.project_browser_bulk_ui import render_bulk_management_panel
from app_modules.project_browser_controls import ProjectBrowserQuery, render_project_browser_controls
from app_modules.project_browser_detail_ui import render_selected_project_panel
from app_modules.project_browser_list_ui import ProjectTableSelection, render_project_table
from app_modules.project_browser_paging import PROJECT_PAGE_SIZE, ProjectPage
from app_modules.project_browser_state import (
    browser_page_index,
    clear_bulk_action,
    clear_delete_confirmation,
    clear_file_delete_confirmation,
    clear_open_candidate,
    clear_rename_candidate,
    remember_selected_project,
    remember_selected_projects,
    selected_project_id,
    selected_project_ids,
    set_browser_page_index,
    sync_project_query,
)
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_io import (
    cancel_pending_project_json_import,
    confirm_pending_project_json_import,
    pending_project_json_import,
    request_project_json_import,
)
from app_modules.project_storage_runtime import project_storage_is_configured
from app_modules.project_storage_service import (
    list_cloud_itinerary_page,
    list_cloud_project_explorer_page,
)
from app_modules.session_state_keys import (
    OPEN_PROJECT_BROWSER_VISIBLE_KEY,
    PROJECT_STORAGE_BROWSER_SUCCESS_KEY,
    PROJECT_STORAGE_BROWSER_WARNING_KEY,
    PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY,
)
from project_storage.errors import storage_user_message


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
                <span>Find, organize, open, copy or delete saved itineraries.</span>
              </div>
            </div>
            """
        )
    with close_col:
        if st.button("Close", key="close_open_project_browser", use_container_width=True):
            cancel_pending_project_json_import()
            clear_bulk_action(st.session_state)
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
    """Render one exact-count project page with durable table selection."""

    _render_browser_messages()
    with st.container(border=True, key="cloud_project_explorer"):
        query = render_project_browser_controls()
        sync_project_query(
            st.session_state,
            search=query.search,
            sort=query.sort,
            owner_slug=query.owner_slug,
            folder_name=query.folder_name,
            view="projects",
        )
        page_index = browser_page_index(st.session_state)
        page, management_ready = _load_project_page(query, page_index=page_index)
        if page is None:
            return
        if not page.projects:
            if page.has_previous:
                set_browser_page_index(st.session_state, page.last_page_index)
                st.rerun()
            _render_empty_state(query)
            return

        active_id = active_project_id_from_state(st.session_state)
        st.markdown("#### Saved projects")
        selection = _render_table(page, active_id=active_id, query=query)
        selected_ids = _select_projects(selection.project_ids)
        if len(selected_ids) > 1:
            render_bulk_management_panel(page, selected_ids=selected_ids, query=query)
        elif len(selected_ids) == 1:
            selected = next(
                (
                    project
                    for project in page.projects
                    if str(project.get("id") or "").strip() == selected_ids[0]
                ),
                None,
            )
            render_selected_project_panel(selected, query=query)
        else:
            render_selected_project_panel(None, query=query)

        if not management_ready:
            st.caption(
                "Basic project browsing is active. Apply the bundled Supabase organization migration "
                "before using owner and folder filters."
            )



def _select_projects(project_ids: object) -> tuple[str, ...]:
    """Apply durable table selection without erasing confirmations on harmless reruns."""

    values = project_ids if isinstance(project_ids, (list, tuple, set)) else (project_ids,)
    clean_ids = tuple(
        dict.fromkeys(
            str(value or "").strip()
            for value in values
            if str(value or "").strip()
        )
    )
    previous = selected_project_ids(st.session_state)
    if clean_ids == previous:
        remember_selected_projects(st.session_state, clean_ids)
        return clean_ids
    remember_selected_projects(st.session_state, clean_ids)
    clear_open_candidate(st.session_state)
    clear_rename_candidate(st.session_state)
    clear_delete_confirmation(st.session_state)
    clear_file_delete_confirmation(st.session_state)
    clear_bulk_action(st.session_state)
    return clean_ids


def _select_project(project_id: object) -> None:
    """Compatibility helper for tests and older one-selection callers."""

    _select_projects((project_id,) if str(project_id or "").strip() else ())

def _render_table(
    page: ProjectPage,
    *,
    active_id: str,
    query: ProjectBrowserQuery,
) -> ProjectTableSelection:
    return render_project_table(
        page,
        selected_project_id=selected_project_id(st.session_state),
        active_project_id=active_id,
        search=query.search,
        sort=query.sort,
        owner_slug=query.owner_slug,
        folder_name=query.folder_name,
    )


def _load_project_page(
    query: ProjectBrowserQuery,
    *,
    page_index: int,
) -> tuple[ProjectPage | None, bool]:
    try:
        page = list_cloud_project_explorer_page(
            page_index=page_index,
            page_size=PROJECT_PAGE_SIZE,
            search=query.search,
            sort=query.sort,
            owner_slug=query.owner_slug,
            folder_name=query.folder_name,
            trash_only=False,
        )
        return page, True
    except Exception:
        can_fallback = (
            not query.owner_slug
            and not query.folder_name
            and query.sort in {"recent", "oldest", "name", "created_recent", "created_oldest"}
        )
        if not can_fallback:
            st.error(
                "Project organization is not available yet. Apply the bundled Supabase migration, "
                "then refresh Project Explorer."
            )
            return None, False
        try:
            page = list_cloud_itinerary_page(
                page_index=page_index,
                page_size=PROJECT_PAGE_SIZE,
                search=query.search,
                sort=query.sort,
            )
        except Exception:
            st.warning(storage_user_message("list"))
            return None, False
        return page, False


def _render_empty_state(query: ProjectBrowserQuery) -> None:
    if query.search or query.owner_slug or query.folder_name:
        st.html(
            """
            <div class="cloud-project-empty-state">
              <strong>No matching projects</strong>
              <span>Reset or adjust the filters to see more saved itineraries.</span>
            </div>
            """
        )
        return
    st.html(
        """
        <div class="cloud-project-empty-state">
          <strong>No cloud projects saved yet</strong>
          <span>Use Save project to create the first cloud project.</span>
        </div>
        """
    )


def _render_browser_messages() -> None:
    cleanup_warning = st.session_state.pop(PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY, "")
    if cleanup_warning:
        st.warning(str(cleanup_warning))
    warning_message = st.session_state.pop(PROJECT_STORAGE_BROWSER_WARNING_KEY, "")
    if warning_message:
        st.warning(str(warning_message))
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
