"""Selectable file-explorer table for saved cloud projects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha1
from typing import Any

import streamlit as st

from app_modules.project_browser_formatting import short_storage_time
from app_modules.project_browser_paging import ProjectPage
from app_modules.project_browser_state import remember_selected_project, set_browser_page_index

PROJECT_TABLE_HEIGHT = 360


def render_project_table(
    page: ProjectPage,
    *,
    selected_project_id: str,
    active_project_id: str,
    search: str,
    sort: str,
) -> str:
    """Render one bounded, selectable project table and return the selected id."""

    rows = project_table_rows(
        page,
        selected_project_id=selected_project_id,
        active_project_id=active_project_id,
    )
    event = st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        height=PROJECT_TABLE_HEIGHT,
        on_select="rerun",
        selection_mode="single-row",
        key=_project_table_key(page, search=search, sort=sort),
    )
    _render_page_navigation(page)
    selected_from_event = project_id_from_table_event(event, page)
    return selected_from_event or selected_project_id


def project_table_rows(
    page: ProjectPage,
    *,
    selected_project_id: str = "",
    active_project_id: str = "",
) -> tuple[dict[str, str], ...]:
    """Return display-only rows without leaking durable project ids into the table."""

    rows: list[dict[str, str]] = []
    for project in page.projects:
        project_id = str(project.get("id") or "").strip()
        status = str(project.get("status") or "draft").replace("_", " ").title()
        if project_id == active_project_id:
            status = f"Active · {status}"
        elif project_id == selected_project_id:
            status = f"Selected · {status}"
        rows.append(
            {
                "Name": str(project.get("name") or "Untitled itinerary"),
                "Status": status,
                "Modified": short_storage_time(project.get("updated_at") or project.get("created_at")),
                "Created": short_storage_time(project.get("created_at")),
            }
        )
    return tuple(rows)


def project_id_from_table_event(event: object, page: ProjectPage) -> str:
    """Resolve Streamlit's row-selection event to the page's durable project id."""

    selection = event.get("selection") if isinstance(event, Mapping) else getattr(event, "selection", None)
    rows = selection.get("rows") if isinstance(selection, Mapping) else getattr(selection, "rows", None)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        return ""
    try:
        index = int(rows[0])
    except (TypeError, ValueError):
        return ""
    if index < 0 or index >= len(page.projects):
        return ""
    return str(page.projects[index].get("id") or "").strip()


def _project_table_key(page: ProjectPage, *, search: str, sort: str) -> str:
    ordered_ids = "|".join(str(project.get("id") or "").strip() for project in page.projects)
    signature = (
        f"{' '.join(str(search or '').split()).casefold()}|"
        f"{str(sort or '').strip().casefold()}|{ordered_ids}"
    )
    digest = sha1(signature.encode("utf-8")).hexdigest()[:10]
    return f"cloud_project_table_{page.page_index}_{digest}"


def _render_page_navigation(page: ProjectPage) -> None:
    previous_col, status_col, next_col = st.columns([0.24, 0.52, 0.24], gap="small")
    with previous_col:
        if st.button(
            "Previous",
            key="cloud_project_page_previous",
            use_container_width=True,
            disabled=not page.has_previous,
        ):
            set_browser_page_index(st.session_state, page.page_index - 1)
            remember_selected_project(st.session_state, "")
            st.rerun()
    with status_col:
        st.caption(f"Page {page.number} · {len(page.projects)} projects shown")
    with next_col:
        if st.button(
            "Next",
            key="cloud_project_page_next",
            use_container_width=True,
            disabled=not page.has_next,
        ):
            set_browser_page_index(st.session_state, page.page_index + 1)
            remember_selected_project(st.session_state, "")
            st.rerun()
