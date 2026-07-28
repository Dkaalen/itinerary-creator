"""Small state helpers for the compact cloud-project manager."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe
from typing import Any

DELETE_CANDIDATE_ID_KEY = "open_project_delete_candidate_id"
DELETE_CANDIDATE_NAME_KEY = "open_project_delete_candidate_name"
FILE_DELETE_CANDIDATE_ID_KEY = "open_project_file_delete_candidate_id"
FILE_DELETE_CANDIDATE_NAME_KEY = "open_project_file_delete_candidate_name"
RENAME_CANDIDATE_ID_KEY = "open_project_rename_candidate_id"
OPEN_CANDIDATE_ID_KEY = "open_project_unsaved_open_candidate_id"
SELECTED_PROJECT_ID_KEY = "open_project_selected_project_id"
SELECTED_PROJECT_IDS_KEY = "open_project_selected_project_ids"
SELECTED_PROJECT_RECORDS_KEY = "open_project_selected_project_records"
PROJECT_EXPLORER_LAST_EVENT_ID_KEY = "open_project_explorer_last_event_id"
PROJECT_EXPLORER_SESSION_ID_KEY = "open_project_explorer_session_id"
PROJECT_PAGE_KEY = "open_project_page_index"
PROJECT_QUERY_SIGNATURE_KEY = "open_project_query_signature"
PROJECT_TABLE_REVISION_KEY = "open_project_table_revision"
BULK_ACTION_KEY = "open_project_bulk_action"
BULK_ACTION_PROJECT_IDS_KEY = "open_project_bulk_action_project_ids"
BULK_ACTION_PROJECT_NAMES_KEY = "open_project_bulk_action_project_names"
BULK_ACTION_TOKEN_KEY = "open_project_bulk_action_token"
BULK_ACTION_LIST_REVISION_KEY = "open_project_bulk_action_list_revision"
FOLDER_OPTIONS_CACHE_KEY = "open_project_folder_options_cache"


@dataclass(frozen=True)
class PendingProjectAction:
    """One immutable management intent bound to a list revision."""

    action: str = ""
    project_ids: tuple[str, ...] = ()
    project_names: tuple[str, ...] = ()
    token: str = ""
    list_revision: int = 0


def project_action_token_fingerprint(token: object) -> str:
    """Return a non-replayable identifier for safe diagnostics."""

    value = str(token or "").strip()
    return sha256(value.encode("utf-8")).hexdigest()[:12] if value else ""


def project_explorer_session_id(state: MutableMapping[str, Any]) -> str:
    """Return a tab-session selection namespace that survives only Streamlit reruns."""

    value = str(state.get(PROJECT_EXPLORER_SESSION_ID_KEY) or "").strip()
    if not value:
        value = token_urlsafe(12)
        state[PROJECT_EXPLORER_SESSION_ID_KEY] = value
    return value


def remember_project_explorer_event(state: MutableMapping[str, Any], event_id: object) -> bool:
    """Return ``True`` only for a new explicit component event."""

    clean_id = str(event_id or "").strip()
    if not clean_id or str(state.get(PROJECT_EXPLORER_LAST_EVENT_ID_KEY) or "") == clean_id:
        return False
    state[PROJECT_EXPLORER_LAST_EVENT_ID_KEY] = clean_id
    return True


def remember_selected_project_records(
    state: MutableMapping[str, Any],
    projects: object,
) -> tuple[dict[str, Any], ...]:
    """Persist small selected-project display records keyed by durable ID."""

    values = projects if isinstance(projects, (list, tuple)) else ()
    records: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, dict):
            continue
        project_id = str(value.get("id") or "").strip()
        if not project_id:
            continue
        records[project_id] = {
            "id": project_id,
            "name": str(value.get("name") or "Untitled itinerary"),
            "owner": str(value.get("owner") or "Unassigned"),
            "folder": str(value.get("folder") or "—"),
            "last_saved": str(value.get("last_saved") or "—"),
            "is_open": bool(value.get("is_open")),
        }
    selected = selected_project_ids(state)
    ordered = tuple(records[value] for value in selected if value in records)
    if ordered:
        state[SELECTED_PROJECT_RECORDS_KEY] = ordered
    else:
        state.pop(SELECTED_PROJECT_RECORDS_KEY, None)
    return ordered


def selected_project_records(state: MutableMapping[str, Any]) -> tuple[dict[str, Any], ...]:
    values = state.get(SELECTED_PROJECT_RECORDS_KEY)
    if not isinstance(values, (list, tuple)):
        return ()
    selected = set(selected_project_ids(state))
    return tuple(
        dict(value)
        for value in values
        if isinstance(value, dict) and str(value.get("id") or "").strip() in selected
    )


def remember_delete_candidate(state: MutableMapping[str, Any], *, project_id: str, name: str) -> None:
    state[DELETE_CANDIDATE_ID_KEY] = project_id
    state[DELETE_CANDIDATE_NAME_KEY] = name


def delete_candidate_id(state: MutableMapping[str, Any]) -> str:
    return str(state.get(DELETE_CANDIDATE_ID_KEY) or "")


def clear_delete_confirmation(state: MutableMapping[str, Any]) -> None:
    state.pop(DELETE_CANDIDATE_ID_KEY, None)
    state.pop(DELETE_CANDIDATE_NAME_KEY, None)


def remember_file_delete_candidate(state: MutableMapping[str, Any], *, file_id: str, filename: str) -> None:
    state[FILE_DELETE_CANDIDATE_ID_KEY] = str(file_id or "").strip()
    state[FILE_DELETE_CANDIDATE_NAME_KEY] = str(filename or "calculation.xlsx")


def file_delete_candidate_id(state: MutableMapping[str, Any]) -> str:
    return str(state.get(FILE_DELETE_CANDIDATE_ID_KEY) or "")


def clear_file_delete_confirmation(state: MutableMapping[str, Any]) -> None:
    state.pop(FILE_DELETE_CANDIDATE_ID_KEY, None)
    state.pop(FILE_DELETE_CANDIDATE_NAME_KEY, None)


def remember_rename_candidate(state: MutableMapping[str, Any], project_id: str) -> None:
    state[RENAME_CANDIDATE_ID_KEY] = str(project_id or "").strip()


def rename_candidate_id(state: MutableMapping[str, Any]) -> str:
    return str(state.get(RENAME_CANDIDATE_ID_KEY) or "")


def clear_rename_candidate(state: MutableMapping[str, Any]) -> None:
    state.pop(RENAME_CANDIDATE_ID_KEY, None)


def remember_open_candidate(state: MutableMapping[str, Any], project_id: str) -> None:
    state[OPEN_CANDIDATE_ID_KEY] = str(project_id or "").strip()


def open_candidate_id(state: MutableMapping[str, Any]) -> str:
    return str(state.get(OPEN_CANDIDATE_ID_KEY) or "")


def clear_open_candidate(state: MutableMapping[str, Any]) -> None:
    state.pop(OPEN_CANDIDATE_ID_KEY, None)


def remember_selected_projects(state: MutableMapping[str, Any], project_ids: object) -> tuple[str, ...]:
    """Persist an ordered, de-duplicated set of durable project identifiers."""

    values = project_ids if isinstance(project_ids, (list, tuple, set)) else (project_ids,)
    clean_ids = tuple(
        dict.fromkeys(
            str(value or "").strip()
            for value in values
            if str(value or "").strip()
        )
    )
    if clean_ids:
        state[SELECTED_PROJECT_IDS_KEY] = clean_ids
        state[SELECTED_PROJECT_ID_KEY] = clean_ids[0]
        existing = state.get(SELECTED_PROJECT_RECORDS_KEY)
        if isinstance(existing, (list, tuple)):
            retained = tuple(
                dict(value)
                for value in existing
                if isinstance(value, dict) and str(value.get("id") or "").strip() in set(clean_ids)
            )
            if retained:
                state[SELECTED_PROJECT_RECORDS_KEY] = retained
            else:
                state.pop(SELECTED_PROJECT_RECORDS_KEY, None)
    else:
        state.pop(SELECTED_PROJECT_IDS_KEY, None)
        state.pop(SELECTED_PROJECT_ID_KEY, None)
        state.pop(SELECTED_PROJECT_RECORDS_KEY, None)
    return clean_ids


def selected_project_ids(state: MutableMapping[str, Any]) -> tuple[str, ...]:
    values = state.get(SELECTED_PROJECT_IDS_KEY)
    if isinstance(values, (list, tuple, set)):
        clean = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in values
                if str(value or "").strip()
            )
        )
        if clean:
            return clean
    legacy = str(state.get(SELECTED_PROJECT_ID_KEY) or "").strip()
    return (legacy,) if legacy else ()


def remember_selected_project(state: MutableMapping[str, Any], project_id: object) -> None:
    """Compatibility helper for callers that still select one project."""

    remember_selected_projects(state, (project_id,) if str(project_id or "").strip() else ())


def selected_project_id(state: MutableMapping[str, Any]) -> str:
    selected = selected_project_ids(state)
    return selected[0] if selected else ""


def clear_selected_project_if_matches(state: MutableMapping[str, Any], project_id: object) -> None:
    clean_id = str(project_id or "").strip()
    if clean_id and clean_id in set(selected_project_ids(state)):
        remember_selected_projects(
            state,
            tuple(value for value in selected_project_ids(state) if value != clean_id),
        )


def browser_page_index(state: MutableMapping[str, Any]) -> int:
    try:
        return max(0, int(state.get(PROJECT_PAGE_KEY) or 0))
    except (TypeError, ValueError):
        return 0


def set_browser_page_index(state: MutableMapping[str, Any], page_index: object) -> None:
    try:
        state[PROJECT_PAGE_KEY] = max(0, int(page_index))
    except (TypeError, ValueError):
        state[PROJECT_PAGE_KEY] = 0


def sync_project_query(
    state: MutableMapping[str, Any],
    *,
    search: object,
    sort: object,
    owner_slug: object = "",
    folder_name: object = "",
    view: object = "projects",
) -> bool:
    """Reset paging and transient actions while preserving durable selection."""

    signature = "|".join(
        (
            " ".join(str(search or "").split()).casefold(),
            str(sort or "").strip().casefold(),
            str(owner_slug or "").strip().casefold(),
            " ".join(str(folder_name or "").split()).casefold(),
            str(view or "projects").strip().casefold(),
        )
    )
    previous = str(state.get(PROJECT_QUERY_SIGNATURE_KEY) or "")
    state[PROJECT_QUERY_SIGNATURE_KEY] = signature
    if previous == signature:
        return False
    set_browser_page_index(state, 0)
    clear_open_candidate(state)
    clear_rename_candidate(state)
    clear_delete_confirmation(state)
    clear_file_delete_confirmation(state)
    clear_bulk_action(state)
    return True


def project_table_revision(state: MutableMapping[str, Any]) -> int:
    try:
        return max(0, int(state.get(PROJECT_TABLE_REVISION_KEY) or 0))
    except (TypeError, ValueError):
        return 0


def bump_project_table_revision(state: MutableMapping[str, Any]) -> int:
    revision = project_table_revision(state) + 1
    state[PROJECT_TABLE_REVISION_KEY] = revision
    return revision


def remember_bulk_action(
    state: MutableMapping[str, Any],
    *,
    action: object,
    project_ids: list[str] | tuple[str, ...],
    project_names: list[str] | tuple[str, ...] = (),
    list_revision: int | None = None,
) -> str:
    """Store one confirmation intent and return its one-use token."""

    clean_ids = tuple(dict.fromkeys(str(value or "").strip() for value in project_ids if str(value or "").strip()))
    token = token_urlsafe(18) if clean_ids else ""
    state[BULK_ACTION_KEY] = str(action or "").strip()
    state[BULK_ACTION_PROJECT_IDS_KEY] = clean_ids
    state[BULK_ACTION_PROJECT_NAMES_KEY] = tuple(str(value or "").strip() for value in project_names)
    state[BULK_ACTION_TOKEN_KEY] = token
    state[BULK_ACTION_LIST_REVISION_KEY] = (
        project_table_revision(state) if list_revision is None else max(0, int(list_revision))
    )
    return token


def pending_bulk_action(state: MutableMapping[str, Any]) -> PendingProjectAction:
    action = str(state.get(BULK_ACTION_KEY) or "").strip()
    ids = tuple(
        str(value or "").strip()
        for value in state.get(BULK_ACTION_PROJECT_IDS_KEY, ())
        if str(value or "").strip()
    )
    names = tuple(
        str(value or "").strip()
        for value in state.get(BULK_ACTION_PROJECT_NAMES_KEY, ())
        if str(value or "").strip()
    )
    try:
        revision = max(0, int(state.get(BULK_ACTION_LIST_REVISION_KEY) or 0))
    except (TypeError, ValueError):
        revision = 0
    return PendingProjectAction(
        action=action,
        project_ids=ids,
        project_names=names,
        token=str(state.get(BULK_ACTION_TOKEN_KEY) or "").strip(),
        list_revision=revision,
    )


def bulk_action(state: MutableMapping[str, Any]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Compatibility tuple for older callers and tests."""

    pending = pending_bulk_action(state)
    return pending.action, pending.project_ids, pending.project_names


def consume_bulk_action(
    state: MutableMapping[str, Any],
    *,
    token: object,
    project_ids: object,
    list_revision: object,
) -> PendingProjectAction | None:
    """Consume an exact, current confirmation once; reject stale events."""

    pending = pending_bulk_action(state)
    values = project_ids if isinstance(project_ids, (list, tuple, set)) else ()
    clean_ids = tuple(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))
    try:
        revision = max(0, int(list_revision))
    except (TypeError, ValueError):
        revision = -1
    valid = bool(
        pending.action
        and pending.token
        and str(token or "").strip() == pending.token
        and clean_ids == pending.project_ids
        and revision == pending.list_revision
        and revision == project_table_revision(state)
        and clean_ids == selected_project_ids(state)
    )
    if not valid:
        return None
    clear_bulk_action(state)
    return pending


def clear_bulk_action(state: MutableMapping[str, Any]) -> None:
    state.pop(BULK_ACTION_KEY, None)
    state.pop(BULK_ACTION_PROJECT_IDS_KEY, None)
    state.pop(BULK_ACTION_PROJECT_NAMES_KEY, None)
    state.pop(BULK_ACTION_TOKEN_KEY, None)
    state.pop(BULK_ACTION_LIST_REVISION_KEY, None)


def cached_folder_options(state: MutableMapping[str, Any], signature: str) -> tuple[Any, ...] | None:
    cache = state.get(FOLDER_OPTIONS_CACHE_KEY)
    if not isinstance(cache, dict):
        return None
    value = cache.get(str(signature))
    return tuple(value) if isinstance(value, (list, tuple)) else None


def remember_folder_options(
    state: MutableMapping[str, Any],
    signature: str,
    options: list[Any] | tuple[Any, ...],
) -> None:
    cache = state.get(FOLDER_OPTIONS_CACHE_KEY)
    if not isinstance(cache, dict):
        cache = {}
    cache[str(signature)] = tuple(options)
    state[FOLDER_OPTIONS_CACHE_KEY] = cache


def invalidate_folder_options(state: MutableMapping[str, Any]) -> None:
    state.pop(FOLDER_OPTIONS_CACHE_KEY, None)
