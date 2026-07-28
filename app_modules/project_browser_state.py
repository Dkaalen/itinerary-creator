"""Small state helpers for the compact cloud-project manager."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

DELETE_CANDIDATE_ID_KEY = "open_project_delete_candidate_id"
DELETE_CANDIDATE_NAME_KEY = "open_project_delete_candidate_name"
FILE_DELETE_CANDIDATE_ID_KEY = "open_project_file_delete_candidate_id"
FILE_DELETE_CANDIDATE_NAME_KEY = "open_project_file_delete_candidate_name"
RENAME_CANDIDATE_ID_KEY = "open_project_rename_candidate_id"
OPEN_CANDIDATE_ID_KEY = "open_project_unsaved_open_candidate_id"
SELECTED_PROJECT_ID_KEY = "open_project_selected_project_id"
PROJECT_PAGE_KEY = "open_project_page_index"
PROJECT_QUERY_SIGNATURE_KEY = "open_project_query_signature"
PROJECT_TABLE_REVISION_KEY = "open_project_table_revision"
BULK_ACTION_KEY = "open_project_bulk_action"
BULK_ACTION_PROJECT_IDS_KEY = "open_project_bulk_action_project_ids"
BULK_ACTION_PROJECT_NAMES_KEY = "open_project_bulk_action_project_names"
FOLDER_OPTIONS_CACHE_KEY = "open_project_folder_options_cache"


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


def remember_selected_project(state: MutableMapping[str, Any], project_id: object) -> None:
    clean_id = str(project_id or "").strip()
    if clean_id:
        state[SELECTED_PROJECT_ID_KEY] = clean_id
    else:
        state.pop(SELECTED_PROJECT_ID_KEY, None)


def selected_project_id(state: MutableMapping[str, Any]) -> str:
    return str(state.get(SELECTED_PROJECT_ID_KEY) or "")


def clear_selected_project_if_matches(state: MutableMapping[str, Any], project_id: object) -> None:
    if selected_project_id(state) == str(project_id or "").strip():
        state.pop(SELECTED_PROJECT_ID_KEY, None)


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
    """Reset paging/selection when the list query changes."""

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
    remember_selected_project(state, "")
    clear_open_candidate(state)
    clear_rename_candidate(state)
    clear_delete_confirmation(state)
    clear_file_delete_confirmation(state)
    clear_bulk_action(state)
    bump_project_table_revision(state)
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
) -> None:
    clean_ids = tuple(dict.fromkeys(str(value or "").strip() for value in project_ids if str(value or "").strip()))
    state[BULK_ACTION_KEY] = str(action or "").strip()
    state[BULK_ACTION_PROJECT_IDS_KEY] = clean_ids
    state[BULK_ACTION_PROJECT_NAMES_KEY] = tuple(str(value or "").strip() for value in project_names)


def bulk_action(state: MutableMapping[str, Any]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
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
    return action, ids, names


def clear_bulk_action(state: MutableMapping[str, Any]) -> None:
    state.pop(BULK_ACTION_KEY, None)
    state.pop(BULK_ACTION_PROJECT_IDS_KEY, None)
    state.pop(BULK_ACTION_PROJECT_NAMES_KEY, None)


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
