"""State helpers that separate cloud identity from the last saved baseline."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from typing import Any

from app_modules.session_state_keys import (
    ACTIVE_PROJECT_CLOUD_PERSISTED_KEY,
    PROJECT_STORAGE_LAST_SAVED_BASELINE_KEY,
    PROJECT_STORAGE_LAST_SAVED_VERSION_ID_KEY,
)


def active_cloud_project_is_persisted(state: Mapping[str, Any]) -> bool:
    """Return whether the active project is known to exist in cloud storage."""

    return bool(state.get(ACTIVE_PROJECT_CLOUD_PERSISTED_KEY))


def last_saved_project_baseline(state: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return the read-only last successfully persisted payload reference."""

    payload = state.get(PROJECT_STORAGE_LAST_SAVED_BASELINE_KEY)
    if not isinstance(payload, Mapping):
        return None
    return payload


def mark_cloud_project_persisted(
    state: MutableMapping[str, Any],
    *,
    payload: Mapping[str, Any],
    version_id: object = "",
) -> None:
    """Record one successful cloud save/open without conflating it with dirty state."""

    state[ACTIVE_PROJECT_CLOUD_PERSISTED_KEY] = True
    state[PROJECT_STORAGE_LAST_SAVED_BASELINE_KEY] = deepcopy(dict(payload))
    clean_version_id = str(version_id or "").strip()
    if clean_version_id:
        state[PROJECT_STORAGE_LAST_SAVED_VERSION_ID_KEY] = clean_version_id
    else:
        state.pop(PROJECT_STORAGE_LAST_SAVED_VERSION_ID_KEY, None)


def clear_cloud_project_persisted_state(state: MutableMapping[str, Any]) -> None:
    """Detach the workspace from all cloud-persistence baseline markers."""

    state.pop(ACTIVE_PROJECT_CLOUD_PERSISTED_KEY, None)
    state.pop(PROJECT_STORAGE_LAST_SAVED_BASELINE_KEY, None)
    state.pop(PROJECT_STORAGE_LAST_SAVED_VERSION_ID_KEY, None)


__all__ = [
    "active_cloud_project_is_persisted",
    "clear_cloud_project_persisted_state",
    "last_saved_project_baseline",
    "mark_cloud_project_persisted",
]
