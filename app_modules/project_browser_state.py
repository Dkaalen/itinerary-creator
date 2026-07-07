"""Small state helpers for the cloud-project browser UI."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.project_identity import active_project_id_from_state
from app_modules.project_session_cleanup import clear_active_cloud_project_session

DELETE_CANDIDATE_ID_KEY = "open_project_delete_candidate_id"
DELETE_CANDIDATE_NAME_KEY = "open_project_delete_candidate_name"
def remember_delete_candidate(state: MutableMapping[str, Any], *, project_id: str, name: str) -> None:
    state[DELETE_CANDIDATE_ID_KEY] = project_id
    state[DELETE_CANDIDATE_NAME_KEY] = name


def delete_candidate_id(state: MutableMapping[str, Any]) -> str:
    return str(state.get(DELETE_CANDIDATE_ID_KEY) or "")


def clear_delete_confirmation(state: MutableMapping[str, Any]) -> None:
    state.pop(DELETE_CANDIDATE_ID_KEY, None)
    state.pop(DELETE_CANDIDATE_NAME_KEY, None)


def clear_deleted_project_from_session(state: MutableMapping[str, Any], project_id: str) -> None:
    """Clear active cloud/session caches when the deleted project is open."""

    if active_project_id_from_state(state) != str(project_id or "").strip():
        return
    clear_active_cloud_project_session(state)
