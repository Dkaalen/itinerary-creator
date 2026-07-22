"""Compact paged list for saved cloud projects."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app_modules.project_browser_actions import duplicate_cloud_project_action, request_open_cloud_project
from app_modules.project_browser_formatting import short_storage_time
from app_modules.project_browser_paging import ProjectPage
from app_modules.project_browser_state import (
    clear_delete_confirmation,
    clear_file_delete_confirmation,
    clear_open_candidate,
    clear_rename_candidate,
    remember_delete_candidate,
    remember_rename_candidate,
    remember_selected_project,
    selected_project_id,
    set_browser_page_index,
)
from app_modules.project_identity import active_project_id_from_state


def render_project_list(page: ProjectPage) -> None:
    """Render one compact list page and its navigation controls."""

    st.markdown("#### Saved projects")
    st.caption(f"Page {page.number} · up to {page.page_size} projects")
    for project in page.projects:
        _render_project_row(project)
    _render_page_navigation(page)


def _render_project_row(project: dict[str, Any]) -> None:
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        return
    name = str(project.get("name") or "Untitled itinerary")
    status = str(project.get("status") or "draft").replace("_", " ").title()
    updated = short_storage_time(project.get("updated_at") or project.get("created_at"))
    is_active = active_project_id_from_state(st.session_state) == project_id
    is_selected = selected_project_id(st.session_state) == project_id
    st.html(
        f"""
        <div class="cloud-project-row{' selected' if is_selected else ''}{' active' if is_active else ''}">
          <div><strong>{escape(name)}</strong><span>{escape(status)} · Last saved {escape(updated)}</span></div>
          <small>{'Active' if is_active else 'Selected' if is_selected else ''}</small>
        </div>
        """
    )
    select_col, open_col, menu_col = st.columns([0.50, 0.34, 0.16], gap="small")
    with select_col:
        if st.button(
            "Selected" if is_selected else "View details",
            key=f"select_cloud_project_{project_id}",
            use_container_width=True,
            disabled=is_selected,
        ):
            _select_project(project_id)
    with open_col:
        if st.button(
            "Open",
            key=f"open_cloud_project_{project_id}",
            use_container_width=True,
            type="primary" if not is_active else "secondary",
            disabled=is_active,
        ):
            request_open_cloud_project(project_id)
    with menu_col:
        with st.popover("…", use_container_width=True):
            if st.button("Rename", key=f"rename_cloud_project_{project_id}", use_container_width=True):
                _select_project(project_id)
                remember_rename_candidate(st.session_state, project_id)
                st.rerun()
            if st.button("Duplicate", key=f"duplicate_cloud_project_{project_id}", use_container_width=True):
                duplicate_cloud_project_action(project_id, name)
            if st.button("Delete", key=f"delete_cloud_project_{project_id}", use_container_width=True):
                _select_project(project_id)
                remember_delete_candidate(st.session_state, project_id=project_id, name=name)
                st.rerun()


def _select_project(project_id: str) -> None:
    remember_selected_project(st.session_state, project_id)
    clear_open_candidate(st.session_state)
    clear_rename_candidate(st.session_state)
    clear_delete_confirmation(st.session_state)
    clear_file_delete_confirmation(st.session_state)


def _render_page_navigation(page: ProjectPage) -> None:
    previous_col, page_col, next_col = st.columns([0.34, 0.32, 0.34], gap="small")
    with previous_col:
        if st.button("Previous", key="cloud_project_page_previous", use_container_width=True, disabled=not page.has_previous):
            set_browser_page_index(st.session_state, page.page_index - 1)
            remember_selected_project(st.session_state, "")
            st.rerun()
    with page_col:
        st.caption(f"Page {page.number}")
    with next_col:
        if st.button("Next", key="cloud_project_page_next", use_container_width=True, disabled=not page.has_next):
            set_browser_page_index(st.session_state, page.page_index + 1)
            remember_selected_project(st.session_state, "")
            st.rerun()
