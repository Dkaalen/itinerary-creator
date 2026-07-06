"""Single authority for the active itinerary/project id in workflow state."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from typing import Any

ACTIVE_PROJECT_STORAGE_ID_KEY = "active_project_storage_id"
ACTIVE_SAVED_PROJECT_ID_KEY = "active_saved_project_id"
PROJECT_ID_STATE_KEYS = (ACTIVE_PROJECT_STORAGE_ID_KEY, ACTIVE_SAVED_PROJECT_ID_KEY)


def normalize_project_id(value: object) -> str:
    """Return a clean project id string, or an empty string when unavailable."""

    return str(value or "").strip()


def active_project_id_from_state(state: Mapping[str, Any]) -> str:
    """Resolve the current project id from the canonical keys and saved payload."""

    for key in PROJECT_ID_STATE_KEYS:
        project_id = normalize_project_id(state.get(key))
        if project_id:
            return project_id
    return project_id_from_payload(state.get("active_saved_project"))


def project_id_from_payload(payload: object) -> str:
    """Return the saved-project metadata id from a payload-like object."""

    if not isinstance(payload, Mapping):
        return ""
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        return ""
    return normalize_project_id(metadata.get("project_id"))


def set_active_project_id(state: MutableMapping[str, Any], project_id: object) -> str:
    """Persist one active project id across all legacy/current state keys."""

    resolved = normalize_project_id(project_id)
    if not resolved:
        clear_active_project_id(state)
        return ""
    for key in PROJECT_ID_STATE_KEYS:
        state[key] = resolved
    _sync_active_payload_project_id(state, resolved)
    return resolved


def ensure_active_project_id(state: MutableMapping[str, Any], *, project_id: object = "") -> str:
    """Return an active project id, creating and syncing one when needed."""

    resolved = normalize_project_id(project_id) or active_project_id_from_state(state)
    if not resolved:
        resolved = str(uuid.uuid4())
    return set_active_project_id(state, resolved)


def clear_active_project_id(state: MutableMapping[str, Any]) -> None:
    """Remove both current and legacy project-id keys."""

    for key in PROJECT_ID_STATE_KEYS:
        state.pop(key, None)


def project_payload_with_id(payload: Mapping[str, Any], project_id: object) -> dict[str, Any]:
    """Return a saved-project payload copy with metadata.project_id normalized."""

    resolved = normalize_project_id(project_id)
    copied = deepcopy(dict(payload))
    metadata = copied.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["project_id"] = resolved
    copied["metadata"] = metadata
    return copied


def _sync_active_payload_project_id(state: MutableMapping[str, Any], project_id: str) -> None:
    payload = state.get("active_saved_project")
    if not isinstance(payload, Mapping):
        return
    state["active_saved_project"] = project_payload_with_id(payload, project_id)
