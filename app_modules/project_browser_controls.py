"""Compact query and working-user controls for Project Explorer."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app_modules.project_browser_state import (
    cached_folder_options,
    remember_folder_options,
)
from app_modules.project_storage_service import list_cloud_project_folders
from app_modules.session_state_keys import (
    OPEN_PROJECT_ACTOR_KEY,
    OPEN_PROJECT_FOLDER_FILTER_KEY,
    OPEN_PROJECT_MANAGE_MODE_KEY,
    OPEN_PROJECT_OWNER_FILTER_KEY,
    OPEN_PROJECT_SEARCH_KEY,
    OPEN_PROJECT_SORT_KEY,
    OPEN_PROJECT_VIEW_KEY,
)
from project_storage.project_metadata import (
    PROJECT_ACTOR_SLUGS,
    PROJECT_OWNER_LABELS,
    PROJECT_OWNER_SLUGS,
)

_SORT_LABELS = {
    "recent": "Recently saved",
    "oldest": "Oldest saved",
    "name": "Name A–Z",
    "created_recent": "Newest created",
    "created_oldest": "Oldest created",
    "owner": "Owner",
    "folder": "Folder/reference",
    "trash_recent": "Recently deleted",
}
_ACTIVE_SORTS = (
    "recent",
    "oldest",
    "name",
    "owner",
    "folder",
    "created_recent",
    "created_oldest",
)
_TRASH_SORTS = ("trash_recent", "name", "owner", "folder", "created_recent")
_VIEW_LABELS = {"projects": "Projects", "trash": "Trash"}


@dataclass(frozen=True)
class ProjectBrowserQuery:
    """Applied Project Explorer query and current organizational actor."""

    search: str = ""
    sort: str = "recent"
    owner_slug: str = ""
    folder_name: str = ""
    view: str = "projects"
    manage_mode: bool = False
    actor_slug: str = "dennis"

    @property
    def trash_only(self) -> bool:
        return self.view == "trash"


def render_project_browser_controls() -> ProjectBrowserQuery:
    """Render compact server-query controls without searching on every keystroke."""

    view, actor_slug, manage_mode = _render_mode_controls()
    folders = _folder_options()
    sorts = _TRASH_SORTS if view == "trash" else _ACTIVE_SORTS
    _normalize_widget_state(sorts=sorts, folders=folders)

    with st.form("project_explorer_filter_form", border=False):
        search_col, owner_col, folder_col, sort_col = st.columns([0.36, 0.18, 0.25, 0.21], gap="small")
        with search_col:
            search = st.text_input(
                "Search",
                key=OPEN_PROJECT_SEARCH_KEY,
                placeholder="Name or folder/reference…",
            )
        with owner_col:
            owner_slug = st.selectbox(
                "Owner",
                ("",) + PROJECT_OWNER_SLUGS,
                key=OPEN_PROJECT_OWNER_FILTER_KEY,
                format_func=lambda value: "All owners" if not value else PROJECT_OWNER_LABELS[value],
            )
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
        apply_col, clear_col, spacer_col = st.columns([0.18, 0.18, 0.64], gap="small")
        with apply_col:
            apply_filters = st.form_submit_button("Apply filters", use_container_width=True, type="primary")
        with clear_col:
            clear_filters = st.form_submit_button("Clear", use_container_width=True)
        with spacer_col:
            st.caption("Search is applied when you press Apply filters, avoiding a cloud request for every keystroke.")

    if clear_filters:
        st.session_state[OPEN_PROJECT_SEARCH_KEY] = ""
        st.session_state[OPEN_PROJECT_OWNER_FILTER_KEY] = ""
        st.session_state[OPEN_PROJECT_FOLDER_FILTER_KEY] = ""
        st.session_state[OPEN_PROJECT_SORT_KEY] = "trash_recent" if view == "trash" else "recent"
        st.rerun()
    if apply_filters:
        # The form submission itself causes the rerun; this branch documents the
        # intentional submit boundary and keeps the returned values authoritative.
        pass

    return ProjectBrowserQuery(
        search=" ".join(str(search or "").split()),
        sort=str(sort or ("trash_recent" if view == "trash" else "recent")),
        owner_slug=str(owner_slug or ""),
        folder_name=str(folder_name or ""),
        view=view,
        manage_mode=manage_mode,
        actor_slug=actor_slug,
    )


def _render_mode_controls() -> tuple[str, str, bool]:
    _ensure_choice(OPEN_PROJECT_VIEW_KEY, _VIEW_LABELS, "projects")
    _ensure_choice(OPEN_PROJECT_ACTOR_KEY, PROJECT_ACTOR_SLUGS, "dennis")
    view_col, actor_col, manage_col = st.columns([0.34, 0.33, 0.33], gap="small")
    with view_col:
        view = st.selectbox(
            "View",
            tuple(_VIEW_LABELS),
            key=OPEN_PROJECT_VIEW_KEY,
            format_func=lambda value: _VIEW_LABELS[value],
        )
    with actor_col:
        actor_slug = st.selectbox(
            "Working as",
            PROJECT_ACTOR_SLUGS,
            key=OPEN_PROJECT_ACTOR_KEY,
            format_func=lambda value: PROJECT_OWNER_LABELS[value],
            help="Used for project organization and Trash history. This is not access control.",
        )
    with manage_col:
        manage_mode = st.checkbox(
            "Manage multiple projects",
            key=OPEN_PROJECT_MANAGE_MODE_KEY,
            help="Select several rows to change owner/folder, move to Trash, restore or permanently delete.",
        )
    return str(view), str(actor_slug), bool(manage_mode)


def _folder_options() -> tuple[str, ...]:
    signature = "all|including-trash"
    cached = cached_folder_options(st.session_state, signature)
    if cached is not None:
        return tuple(str(value) for value in cached)
    try:
        options = list_cloud_project_folders(include_trashed=True)
    except Exception:
        options = ()
    folders = tuple(option.folder_name for option in options if option.folder_name)
    remember_folder_options(st.session_state, signature, folders)
    return folders


def _normalize_widget_state(*, sorts: tuple[str, ...], folders: tuple[str, ...]) -> None:
    _ensure_choice(OPEN_PROJECT_SORT_KEY, sorts, sorts[0])
    _ensure_choice(OPEN_PROJECT_OWNER_FILTER_KEY, ("",) + PROJECT_OWNER_SLUGS, "")
    _ensure_choice(OPEN_PROJECT_FOLDER_FILTER_KEY, ("",) + folders, "")


def _ensure_choice(key: str, choices: object, default: str) -> None:
    allowed = tuple(choices)
    if st.session_state.get(key) not in allowed:
        st.session_state[key] = default
