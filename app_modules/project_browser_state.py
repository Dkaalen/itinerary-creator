"""Small state helpers for the cloud-project browser UI."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

DELETE_CANDIDATE_ID_KEY = "open_project_delete_candidate_id"
DELETE_CANDIDATE_NAME_KEY = "open_project_delete_candidate_name"
FILE_DELETE_CANDIDATE_ID_KEY = "open_project_file_delete_candidate_id"
FILE_DELETE_CANDIDATE_NAME_KEY = "open_project_file_delete_candidate_name"

RENAME_CANDIDATE_ID_KEY = "open_project_rename_candidate_id"
OPEN_CANDIDATE_ID_KEY = "open_project_unsaved_open_candidate_id"


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
