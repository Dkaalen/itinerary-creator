"""Compact query controls for Project Explorer."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app_modules.project_browser_state import cached_folder_options, remember_folder_options
from app_modules.project_storage_service import list_cloud_project_folders
from app_modules.session_state_keys import (
    OPEN_PROJECT_FOLDER_FILTER_KEY,
    OPEN_PROJECT_OWNER_FILTER_KEY,
    OPEN_PROJECT_SEARCH_KEY,
    OPEN_PROJECT_SORT_KEY,
)
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
_SORTS = tuple(_SORT_LABELS)


@dataclass(frozen=True)
class ProjectBrowserQuery:
    """Applied Project Explorer query."""

    search: str = ""
    sort: str = "recent"
    owner_slug: str = ""
    folder_name: str = ""
    view: str = "projects"
    actor_slug: str = "dennis"

    @property
    def trash_only(self) -> bool:
        return False


def render_project_browser_controls() -> ProjectBrowserQuery:
    """Render one compact, submitted server-query toolbar."""

    folders = _folder_options()
    _normalize_widget_state(folders=folders)
    with st.form("project_explorer_filter_form", border=False):
        search_col, owner_col, folder_col, sort_col = st.columns(
            [0.37, 0.18, 0.25, 0.20],
            gap="small",
            vertical_alignment="bottom",
        )
        with search_col:
            search = st.text_input(
                "Search projects",
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
                _SORTS,
                key=OPEN_PROJECT_SORT_KEY,
                format_func=lambda value: _SORT_LABELS[value],
            )
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
    )


def _folder_options() -> tuple[str, ...]:
    signature = "all|including-legacy-soft-deleted"
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


def _normalize_widget_state(*, folders: tuple[str, ...]) -> None:
    _ensure_choice(OPEN_PROJECT_SORT_KEY, _SORTS, "recent")
    _ensure_choice(OPEN_PROJECT_OWNER_FILTER_KEY, ("",) + PROJECT_OWNER_SLUGS, "")
    _ensure_choice(OPEN_PROJECT_FOLDER_FILTER_KEY, ("",) + folders, "")


def _ensure_choice(key: str, choices: object, default: str) -> None:
    allowed = tuple(choices)
    if st.session_state.get(key) not in allowed:
        st.session_state[key] = default
