"""Compact query controls for Project Explorer."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app_modules.performance_telemetry import measure_timing, record_trace, telemetry_is_active
from app_modules.project_storage_service import list_cloud_project_folders
from app_modules.session_state_keys import (
    OPEN_PROJECT_FOLDER_FILTER_KEY,
    OPEN_PROJECT_OWNER_FILTER_KEY,
    OPEN_PROJECT_SEARCH_KEY,
    OPEN_PROJECT_SORT_KEY,
)
from project_storage.capabilities import ProjectStorageCapabilities
from project_storage.project_metadata import PROJECT_OWNER_LABELS, PROJECT_OWNER_SLUGS

_SORT_LABELS = {
    "recent": "Recently saved",
    "oldest": "Oldest saved",
    "name": "Name A–Z",
    "owner": "Owner",
    "folder": "Folder/reference",
    "created_recent": "Newest created",
    "created_oldest": "Oldest created",
}
_LEGACY_SORTS = ("recent", "oldest", "name", "created_recent", "created_oldest")


@dataclass(frozen=True)
class ProjectBrowserQuery:
    """Applied Project Explorer query."""

    search: str = ""
    sort: str = "recent"
    owner_slug: str = ""
    folder_name: str = ""
    view: str = "projects"
    actor_slug: str = "dennis"
    organization_available: bool = False


def render_project_browser_controls(
    capabilities: ProjectStorageCapabilities | None = None,
) -> ProjectBrowserQuery:
    """Render one submitted toolbar with only supported backend controls."""

    capabilities = capabilities or ProjectStorageCapabilities.legacy()
    current_owner = str(st.session_state.get(OPEN_PROJECT_OWNER_FILTER_KEY) or "").strip().casefold()
    if current_owner not in PROJECT_OWNER_SLUGS:
        current_owner = ""
    folders = _folder_options(capabilities, owner_slug=current_owner)
    sorts = _sort_options(capabilities)
    _normalize_widget_state(folders=folders, sorts=sorts, capabilities=capabilities)

    with st.form("project_explorer_filter_form", border=False):
        with st.container(key="project_explorer_filter_fields"):
            if capabilities.organization_controls and capabilities.folder_filter:
                search_col, owner_col, folder_col, sort_col = st.columns(
                    [0.37, 0.18, 0.25, 0.20],
                    gap="small",
                    vertical_alignment="bottom",
                )
            elif capabilities.organization_controls:
                search_col, owner_col, sort_col = st.columns(
                    [0.52, 0.22, 0.26],
                    gap="small",
                    vertical_alignment="bottom",
                )
                folder_col = None
            else:
                search_col, sort_col = st.columns(
                    [0.72, 0.28],
                    gap="small",
                    vertical_alignment="bottom",
                )
                owner_col = None
                folder_col = None

            with search_col:
                search = st.text_input(
                    "Search projects",
                    key=OPEN_PROJECT_SEARCH_KEY,
                    placeholder="Name, folder or reference",
                )

            owner_slug = ""
            if owner_col is not None:
                with owner_col:
                    owner_slug = st.selectbox(
                        "Owner",
                        ("",) + PROJECT_OWNER_SLUGS,
                        key=OPEN_PROJECT_OWNER_FILTER_KEY,
                        format_func=lambda value: "All owners" if not value else PROJECT_OWNER_LABELS[value],
                    )

            folder_name = ""
            if folder_col is not None:
                with folder_col:
                    folder_name = st.selectbox(
                        "Folder/reference",
                        ("",) + folders,
                        key=OPEN_PROJECT_FOLDER_FILTER_KEY,
                        format_func=lambda value: "All folders" if not value else value,
                    )

            with sort_col:
                sort = st.selectbox(
                    "Sort",
                    sorts,
                    key=OPEN_PROJECT_SORT_KEY,
                    format_func=lambda value: _SORT_LABELS[value],
                )

        with st.container(key="project_explorer_filter_actions"):
            action_col, reset_col, spacer_col = st.columns([0.16, 0.16, 0.68], gap="small")
            with action_col:
                st.form_submit_button("Apply", use_container_width=True, type="primary")
            with reset_col:
                reset = st.form_submit_button("Reset", use_container_width=True)
            with spacer_col:
                st.empty()

    if reset:
        st.session_state[OPEN_PROJECT_SEARCH_KEY] = ""
        st.session_state[OPEN_PROJECT_OWNER_FILTER_KEY] = ""
        st.session_state[OPEN_PROJECT_FOLDER_FILTER_KEY] = ""
        st.session_state[OPEN_PROJECT_SORT_KEY] = "recent"
        st.rerun()

    return ProjectBrowserQuery(
        search=" ".join(str(search or "").split()),
        sort=str(sort or "recent"),
        owner_slug=str(owner_slug or ""),
        folder_name=str(folder_name or ""),
        organization_available=capabilities.organization_controls,
    )


def _folder_options(
    capabilities: ProjectStorageCapabilities,
    *,
    owner_slug: str = "",
) -> tuple[str, ...]:
    if not capabilities.folder_filter:
        return ()
    state = st.session_state if telemetry_is_active(st.session_state) else None
    try:
        with measure_timing(state, "project_folder_list"):
            options = list_cloud_project_folders(owner_slug=owner_slug)
    except Exception as exc:
        if state is not None:
            record_trace(
                state,
                "project_folder_list_failed",
                error_type=type(exc).__name__,
            )
        return ()
    folders = tuple(option.folder_name for option in options if option.folder_name)
    if state is not None:
        record_trace(state, "project_folder_list_completed", folder_count=len(folders))
    return folders


def _sort_options(capabilities: ProjectStorageCapabilities) -> tuple[str, ...]:
    if not capabilities.organization_controls:
        return _LEGACY_SORTS
    options = list(_LEGACY_SORTS)
    options.append("owner")
    if capabilities.folder_filter:
        options.append("folder")
    return tuple(options)


def _normalize_widget_state(
    *,
    folders: tuple[str, ...],
    sorts: tuple[str, ...],
    capabilities: ProjectStorageCapabilities,
) -> None:
    _ensure_choice(OPEN_PROJECT_SORT_KEY, sorts, "recent")
    owner_choices = ("",) + PROJECT_OWNER_SLUGS if capabilities.organization_controls else ("",)
    folder_choices = ("",) + folders if capabilities.folder_filter else ("",)
    _ensure_choice(OPEN_PROJECT_OWNER_FILTER_KEY, owner_choices, "")
    _ensure_choice(OPEN_PROJECT_FOLDER_FILTER_KEY, folder_choices, "")


def _ensure_choice(key: str, choices: object, default: str) -> None:
    allowed = tuple(choices)
    if st.session_state.get(key) not in allowed:
        st.session_state[key] = default
