"""Small state helpers for the cloud-project browser UI."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.project_identity import clear_active_project_id

DELETE_CANDIDATE_ID_KEY = "open_project_delete_candidate_id"
DELETE_CANDIDATE_NAME_KEY = "open_project_delete_candidate_name"
_ACTIVE_PROJECT_KEYS = (
    "active_saved_project",
    "project_storage_last_saved_snapshot_path",
    "project_storage_last_calculator_file_path",
    "project_storage_last_pdf_path",
)


def remember_delete_candidate(state: MutableMapping[str, Any], *, project_id: str, name: str) -> None:
    state[DELETE_CANDIDATE_ID_KEY] = project_id
    state[DELETE_CANDIDATE_NAME_KEY] = name


def delete_candidate_id(state: MutableMapping[str, Any]) -> str:
    return str(state.get(DELETE_CANDIDATE_ID_KEY) or "")


def clear_delete_confirmation(state: MutableMapping[str, Any]) -> None:
    state.pop(DELETE_CANDIDATE_ID_KEY, None)
    state.pop(DELETE_CANDIDATE_NAME_KEY, None)


def clear_deleted_project_from_session(state: MutableMapping[str, Any], project_id: str) -> None:
    if str(state.get("active_project_storage_id") or "") != str(project_id or ""):
        return
    for key in _ACTIVE_PROJECT_KEYS:
        state.pop(key, None)
    clear_active_project_id(state)
