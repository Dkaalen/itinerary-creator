"""Selectable file-explorer table for saved cloud projects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha1

import streamlit as st

from app_modules.project_browser_formatting import friendly_storage_time
from app_modules.project_browser_paging import ProjectPage
from app_modules.project_browser_state import (
    project_table_revision,
    selected_project_ids,
    set_browser_page_index,
)
from project_storage.project_metadata import project_owner_label

PROJECT_TABLE_HEIGHT = 330


@dataclass(frozen=True)
class ProjectTableSelection:
    """Durable project IDs selected from one rendered server page."""

    project_ids: tuple[str, ...] = ()

    @property
    def primary_id(self) -> str:
        return self.project_ids[0] if self.project_ids else ""


def render_project_table(
    page: ProjectPage,
    *,
    selected_project_id: str = "",
    active_project_id: str,
    search: str,
    sort: str,
    owner_slug: str = "",
    folder_name: str = "",
    view: str = "projects",
) -> ProjectTableSelection:
    """Render one bounded page and persist only durable selected IDs.

    Streamlit row indexes are converted immediately to project identifiers. An
    explicit empty selection clears the prior selection; it never silently
    re-selects the previous project or the first row.
    """

    del selected_project_id, view  # Retained in the signature for compatibility.
    rows = project_table_rows(page, active_project_id=active_project_id)
    event = st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        height=PROJECT_TABLE_HEIGHT,
        on_select="rerun",
        selection_mode="multi-row",
        key=_project_table_key(
            page,
            search=search,
            sort=sort,
            owner_slug=owner_slug,
            folder_name=folder_name,
            revision=project_table_revision(st.session_state),
        ),
        column_config=_column_config(),
    )
    selected = _selection_from_event(event, page)
    if selected is None:
        page_ids = {str(project.get("id") or "").strip() for project in page.projects}
        selected = tuple(value for value in selected_project_ids(st.session_state) if value in page_ids)
    _render_page_navigation(page)
    return ProjectTableSelection(tuple(selected))


def project_table_rows(
    page: ProjectPage,
    *,
    selected_project_id: str = "",
    active_project_id: str = "",
    trash_only: bool = False,
) -> tuple[dict[str, str], ...]:
    """Return a compact display model without technical identifiers."""

    del selected_project_id, trash_only
    rows: list[dict[str, str]] = []
    for project in page.projects:
        project_id = str(project.get("id") or "").strip()
        name = str(project.get("name") or "Untitled itinerary")
        if project_id and project_id == active_project_id:
            name = f"{name} · Open"
        rows.append(
            {
                "Name": name,
                "Owner": _owner_label(project.get("owner_slug")),
                "Folder": str(project.get("folder_name") or "—"),
                "Last saved": friendly_storage_time(
                    project.get("last_saved_at")
                    or project.get("updated_at")
                    or project.get("created_at")
                ),
            }
        )
    return tuple(rows)


def _selection_from_event(event: object, page: ProjectPage) -> tuple[str, ...] | None:
    """Return ``None`` only when a stub/component exposes no selection payload."""

    if isinstance(event, Mapping):
        if "selection" not in event:
            return None
        selection = event.get("selection")
    else:
        if not hasattr(event, "selection"):
            return None
        selection = getattr(event, "selection", None)
    if isinstance(selection, Mapping):
        if "rows" not in selection:
            return None
        rows = selection.get("rows")
    else:
        if selection is None or not hasattr(selection, "rows"):
            return None
        rows = getattr(selection, "rows", None)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return ()
    project_ids: list[str] = []
    for raw_index in rows:
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= len(page.projects):
            continue
        project_id = str(page.projects[index].get("id") or "").strip()
        if project_id and project_id not in project_ids:
            project_ids.append(project_id)
    return tuple(project_ids)


def project_ids_from_table_event(event: object, page: ProjectPage) -> tuple[str, ...]:
    selected = _selection_from_event(event, page)
    return selected or ()


def project_id_from_table_event(event: object, page: ProjectPage) -> str:
    selected = project_ids_from_table_event(event, page)
    return selected[0] if selected else ""


def _project_table_key(
    page: ProjectPage,
    *,
    search: str,
    sort: str,
    owner_slug: str = "",
    folder_name: str = "",
    view: str = "projects",
    revision: int = 0,
) -> str:
    ordered_ids = "|".join(str(project.get("id") or "").strip() for project in page.projects)
    signature = "|".join(
        (
            " ".join(str(search or "").split()).casefold(),
            str(sort or "").strip().casefold(),
            str(owner_slug or "").strip().casefold(),
            " ".join(str(folder_name or "").split()).casefold(),
            str(view or "projects").strip().casefold(),
            str(max(0, int(revision))),
            ordered_ids,
        )
    )
    digest = sha1(signature.encode("utf-8")).hexdigest()[:10]
    return f"cloud_project_table_{page.page_index}_{digest}"


def _render_page_navigation(page: ProjectPage) -> None:
    previous_col, status_col, next_col = st.columns([0.22, 0.56, 0.22], gap="small")
    with previous_col:
        if st.button(
            "Previous",
            key="cloud_project_page_previous",
            use_container_width=True,
            disabled=not page.has_previous,
        ):
            set_browser_page_index(st.session_state, page.page_index - 1)
            remember_selected_projects(st.session_state, ())
            st.rerun()
    with status_col:
        if page.total_count is None:
            st.caption(f"Page {page.number} · {len(page.projects)} projects shown")
        elif page.total_count:
            st.caption(
                f"{page.first_item_number}–{page.last_item_number} of {page.total_count} projects"
                f" · Page {page.number} of {page.total_pages}"
            )
        else:
            st.caption("0 projects")
    with next_col:
        if st.button(
            "Next",
            key="cloud_project_page_next",
            use_container_width=True,
            disabled=not page.has_next,
        ):
            set_browser_page_index(st.session_state, page.page_index + 1)
            remember_selected_projects(st.session_state, ())
            st.rerun()


def _owner_label(value: object) -> str:
    try:
        return project_owner_label(value or "unassigned")
    except ValueError:
        return "Unassigned"


def _column_config() -> dict[str, object]:
    text_column = getattr(getattr(st, "column_config", None), "TextColumn", None)
    if text_column is None:
        return {}
    return {
        "Name": text_column("Name", width="large"),
        "Owner": text_column("Owner", width="small"),
        "Folder": text_column("Folder/reference", width="medium"),
        "Last saved": text_column("Last saved", width="medium"),
    }
