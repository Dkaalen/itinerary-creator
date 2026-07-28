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
    project_table_revision,
    clear_bulk_action,
    clear_delete_confirmation,
    clear_file_delete_confirmation,
    clear_open_candidate,
    clear_rename_candidate,
    remember_project_explorer_event,
    remember_selected_project,
    remember_selected_project_records,
    remember_selected_projects,
    selected_project_id,
    selected_project_ids,
    selected_project_records,
    set_browser_page_index,
    sync_project_query,
)
from app_modules.performance_telemetry import measure_timing, record_trace, telemetry_is_active
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_io import (
    cancel_pending_project_json_import,
    confirm_pending_project_json_import,
    pending_project_json_import,
    request_project_json_import,
)
from app_modules.project_storage_runtime import project_storage_is_configured
from app_modules.project_storage_service import (
    cloud_project_capabilities,
    list_cloud_itinerary_page,
    list_cloud_project_explorer_page,
)
from app_modules.session_state_keys import (
    OPEN_PROJECT_BROWSER_VISIBLE_KEY,
    PROJECT_STORAGE_BROWSER_SUCCESS_KEY,
    PROJECT_STORAGE_BROWSER_WARNING_KEY,
    PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY,
)
from project_storage.capabilities import ProjectStorageCapabilities
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

    with st.container(key="project_explorer_workspace"):
        with st.container(key="project_explorer_header"):
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
            st.caption("Saved projects are unavailable in this session. You can still open a backup file below.")
        _render_backup_project_uploader()


def _render_cloud_project_browser() -> None:
    """Render one exact-count project page with durable table selection."""

    state = st.session_state if telemetry_is_active(st.session_state) else None
    with measure_timing(state, "project_explorer_render"):
        _render_cloud_project_browser_content()


def _render_cloud_project_browser_content() -> None:
    _render_browser_messages()
    with st.container(border=True, key="cloud_project_explorer"):
        try:
            capabilities = cloud_project_capabilities()
        except Exception:
            st.warning(storage_user_message("list"))
            return
        if telemetry_is_active(st.session_state):
            record_trace(
                st.session_state,
                "project_storage_capabilities",
                management_schema=capabilities.management_schema,
                folder_listing=capabilities.folder_listing,
                reason=capabilities.reason,
            )
        query = render_project_browser_controls(capabilities)
        sync_project_query(
            st.session_state,
            search=query.search,
            sort=query.sort,
            owner_slug=query.owner_slug,
            folder_name=query.folder_name,
            view="projects",
        )
        page_index = browser_page_index(st.session_state)
        page, _management_ready = _load_project_page(
            query,
            page_index=page_index,
            capabilities=capabilities,
        )
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
        selected_ids = _apply_project_table_event(selection, page=page)
        selected_records = selected_project_records(st.session_state)
        if len(selected_ids) > 1:
            render_bulk_management_panel(
                page,
                selected_ids=selected_ids,
                selected_projects=selected_records,
                query=query,
            )
        elif len(selected_ids) == 1:
            selected = next(
                (
                    project
                    for project in page.projects
                    if str(project.get("id") or "").strip() == selected_ids[0]
                ),
                None,
            )
            if selected is None:
                selected = next(
                    (record for record in selected_records if str(record.get("id") or "").strip() == selected_ids[0]),
                    None,
                )
            render_selected_project_panel(selected, query=query)
        else:
            render_selected_project_panel(None, query=query)


def _apply_project_table_event(
    selection: ProjectTableSelection,
    *,
    page: ProjectPage,
) -> tuple[str, ...]:
    """Apply only a new explicit browser event; checkbox clicks stay client-side."""

    if not selection.event_id or not remember_project_explorer_event(st.session_state, selection.event_id):
        return selected_project_ids(st.session_state)
    if selection.list_revision != project_table_revision(st.session_state):
        clear_bulk_action(st.session_state)
        st.session_state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = (
            "The project list changed before that selection was applied. Review the current list and try again."
        )
        return selected_project_ids(st.session_state)
    selected_ids = _select_projects(selection.project_ids, projects=selection.projects)
    if selection.action == "page" and selection.page_delta:
        target = page.page_index + selection.page_delta
        if selection.page_delta < 0 and not page.has_previous:
            return selected_ids
        if selection.page_delta > 0 and not page.has_next:
            return selected_ids
        set_browser_page_index(st.session_state, target)
        st.rerun()
    return selected_ids


def _select_projects(
    project_ids: object,
    *,
    projects: object = (),
) -> tuple[str, ...]:
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
        if projects:
            remember_selected_project_records(st.session_state, projects)
        return clean_ids
    if telemetry_is_active(st.session_state):
        record_trace(
            st.session_state,
            "project_selection_changed",
            previous_project_ids=previous,
            selected_project_ids=clean_ids,
            list_revision=project_table_revision(st.session_state),
        )
    remember_selected_projects(st.session_state, clean_ids)
    remember_selected_project_records(st.session_state, projects)
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
        selected_project_ids=selected_project_ids(st.session_state),
        selected_projects=selected_project_records(st.session_state),
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
    capabilities: ProjectStorageCapabilities | None = None,
) -> tuple[ProjectPage | None, bool]:
    """Load exactly one supported list path; never fail then issue a hidden fallback."""

    capabilities = capabilities or ProjectStorageCapabilities.legacy()
    state = st.session_state if telemetry_is_active(st.session_state) else None
    management_ready = capabilities.management_schema
    path = "management" if management_ready else "legacy"
    if state is not None:
        record_trace(
            state,
            "project_list_requested",
            path=path,
            page_index=page_index,
            sort=query.sort,
            has_search=bool(query.search),
            has_owner=bool(query.owner_slug),
            has_folder=bool(query.folder_name),
        )
    try:
        with measure_timing(state, f"project_list_{path}", note=query.sort):
            if management_ready:
                page = list_cloud_project_explorer_page(
                    page_index=page_index,
                    page_size=PROJECT_PAGE_SIZE,
                    search=query.search,
                    sort=query.sort,
                    owner_slug=query.owner_slug,
                    folder_name=query.folder_name,
                )
            else:
                page = list_cloud_itinerary_page(
                    page_index=page_index,
                    page_size=PROJECT_PAGE_SIZE,
                    search=query.search,
                    sort=query.sort,
                )
    except Exception as exc:
        if state is not None:
            record_trace(
                state,
                "project_list_failed",
                path=path,
                error_type=type(exc).__name__,
            )
        st.warning(storage_user_message("list"))
        return None, management_ready
    if state is not None:
        record_trace(
            state,
            "project_list_completed",
            path=path,
            project_count=len(page.projects),
            total_count=page.total_count,
        )
    return page, management_ready


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
    with st.container(key="project_explorer_backup"):
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
    with st.container(key="project_explorer_backup_confirmation"):
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
