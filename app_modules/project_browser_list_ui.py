"""Browser-owned selectable table for saved cloud projects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app_modules.project_browser_formatting import friendly_storage_time
from app_modules.project_browser_paging import ProjectPage
from app_modules.project_browser_state import project_explorer_session_id, project_table_revision
from project_explorer_component import render_project_explorer_table
from project_storage.project_metadata import project_owner_label


@dataclass(frozen=True)
class ProjectTableSelection:
    """One explicit client action plus durable project identifiers."""

    project_ids: tuple[str, ...] = ()
    projects: tuple[dict[str, Any], ...] = ()
    action: str = ""
    event_id: str = ""
    list_revision: int = 0
    page_delta: int = 0

    @property
    def primary_id(self) -> str:
        return self.project_ids[0] if self.project_ids else ""


def render_project_table(
    page: ProjectPage,
    *,
    selected_project_id: str = "",
    selected_project_ids: Sequence[str] = (),
    selected_projects: Sequence[Mapping[str, Any]] = (),
    active_project_id: str,
    search: str,
    sort: str,
    owner_slug: str = "",
    folder_name: str = "",
    view: str = "projects",
) -> ProjectTableSelection:
    """Render the table without rerunning Python for checkbox changes.

    Search and sort remain server-owned. Checkbox selection, selection count and
    clearing are client-owned until the user explicitly reviews the selection
    or changes page. Every emitted selection is expressed as durable project
    identifiers, never row indexes.
    """

    del selected_project_id, search, sort, owner_slug, folder_name, view
    payload = {
        "rows": list(project_table_rows(page, active_project_id=active_project_id)),
        "selected_project_ids": list(_clean_ids(selected_project_ids)),
        "selected_projects": [
            project_table_record(project, active_project_id=active_project_id)
            for project in selected_projects
            if str(project.get("id") or "").strip()
        ],
        "list_revision": project_table_revision(_session_state()),
        "selection_session_id": project_explorer_session_id(_session_state()),
        "page_index": page.page_index,
        "page_number": page.number,
        "has_previous": page.has_previous,
        "has_next": page.has_next,
        "first_item_number": page.first_item_number,
        "last_item_number": page.last_item_number,
        "total_count": page.total_count,
        "total_pages": page.total_pages,
    }
    event = render_project_explorer_table(payload)
    return project_table_selection_from_event(event)


def project_table_rows(
    page: ProjectPage,
    *,
    selected_project_id: str = "",
    active_project_id: str = "",
) -> tuple[dict[str, Any], ...]:
    """Return the compact client display model with durable identifiers."""

    del selected_project_id
    return tuple(
        project_table_record(project, active_project_id=active_project_id)
        for project in page.projects
        if str(project.get("id") or "").strip()
    )


def project_table_record(
    project: Mapping[str, Any],
    *,
    active_project_id: str = "",
) -> dict[str, Any]:
    """Normalize one server project for the browser-owned table."""

    project_id = str(project.get("id") or "").strip()
    return {
        "id": project_id,
        "name": str(project.get("name") or "Untitled itinerary"),
        "owner": _owner_label(project.get("owner_slug")),
        "folder": str(project.get("folder_name") or "—"),
        "last_saved": friendly_storage_time(
            project.get("last_saved_at")
            or project.get("updated_at")
            or project.get("created_at")
        ),
        "is_open": bool(project_id and project_id == active_project_id),
    }


def project_table_selection_from_event(event: object) -> ProjectTableSelection:
    """Validate the component result without trusting client row positions."""

    if not isinstance(event, Mapping):
        return ProjectTableSelection()
    event_id = str(event.get("event_id") or "").strip()
    action = str(event.get("action") or "").strip()
    if not event_id or action not in {"commit_selection", "clear_selection", "page"}:
        return ProjectTableSelection()
    ids = _clean_ids(event.get("selected_project_ids"))
    records_by_id: dict[str, dict[str, Any]] = {}
    records = event.get("selected_projects")
    if isinstance(records, Sequence) and not isinstance(records, (str, bytes)):
        for value in records:
            if not isinstance(value, Mapping):
                continue
            project_id = str(value.get("id") or "").strip()
            if not project_id or project_id not in ids:
                continue
            records_by_id[project_id] = {
                "id": project_id,
                "name": str(value.get("name") or "Untitled itinerary"),
                "owner": str(value.get("owner") or "Unassigned"),
                "folder": str(value.get("folder") or "—"),
                "last_saved": str(value.get("last_saved") or "—"),
                "is_open": bool(value.get("is_open")),
            }
    try:
        list_revision = max(0, int(event.get("list_revision") or 0))
    except (TypeError, ValueError):
        list_revision = 0
    try:
        page_delta = int(event.get("page_delta") or 0)
    except (TypeError, ValueError):
        page_delta = 0
    if action != "page" or page_delta not in {-1, 1}:
        page_delta = 0
    return ProjectTableSelection(
        project_ids=ids,
        projects=tuple(records_by_id[project_id] for project_id in ids if project_id in records_by_id),
        action=action,
        event_id=event_id,
        list_revision=list_revision,
        page_delta=page_delta,
    )


def project_ids_from_table_event(event: object, page: ProjectPage | None = None) -> tuple[str, ...]:
    """Return durable IDs directly from the component event."""

    del page
    return project_table_selection_from_event(event).project_ids


def project_id_from_table_event(event: object, page: ProjectPage | None = None) -> str:
    selected = project_ids_from_table_event(event, page)
    return selected[0] if selected else ""


def _clean_ids(values: object) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return ()
    return tuple(
        dict.fromkeys(
            str(value or "").strip()
            for value in values
            if str(value or "").strip()
        )
    )


def _owner_label(value: object) -> str:
    try:
        return project_owner_label(value or "unassigned")
    except ValueError:
        return "Unassigned"


def _session_state() -> Any:
    """Import Streamlit lazily so pure event helpers remain lightweight."""

    import streamlit as st

    return st.session_state


__all__ = [
    "ProjectTableSelection",
    "project_id_from_table_event",
    "project_ids_from_table_event",
    "project_table_record",
    "project_table_rows",
    "project_table_selection_from_event",
    "render_project_table",
]
