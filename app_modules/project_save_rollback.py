"""Capture and restore project identity/baseline around fallible cloud saves."""

from __future__ import annotations

from collections.abc import MutableMapping
from copy import deepcopy
from typing import Any

from app_modules.project_workspace_revision import (
    PERSISTED_BASELINE_SIGNATURES_KEY,
    WORKSPACE_REVISION_KEY,
    WORKSPACE_SIGNATURE_CACHE_KEY,
)
from app_modules.session_state_keys import (
    ACTIVE_PROJECT_CLOUD_PERSISTED_KEY,
    ACTIVE_PROJECT_STORAGE_ID_KEY,
    ACTIVE_SAVED_PROJECT_ID_KEY,
    ACTIVE_SAVED_PROJECT_KEY,
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
    PROJECT_STORAGE_LAST_SAVED_BASELINE_KEY,
    PROJECT_STORAGE_LAST_SAVED_VERSION_ID_KEY,
)

_PROJECT_SAVE_BASELINE_KEYS = (
    ACTIVE_SAVED_PROJECT_KEY,
    ACTIVE_PROJECT_STORAGE_ID_KEY,
    ACTIVE_SAVED_PROJECT_ID_KEY,
    ACTIVE_PROJECT_CLOUD_PERSISTED_KEY,
    PROJECT_STORAGE_LAST_SAVED_BASELINE_KEY,
    PROJECT_STORAGE_LAST_SAVED_VERSION_ID_KEY,
    ITINERARY_NAME_KEY,
    ITINERARY_NAME_INPUT_KEY,
    PERSISTED_BASELINE_SIGNATURES_KEY,
    WORKSPACE_REVISION_KEY,
    WORKSPACE_SIGNATURE_CACHE_KEY,
)
_MISSING = object()


def capture_project_save_baseline(state: MutableMapping[str, Any]) -> dict[str, Any]:
    """Return a deep snapshot of state mutated while preparing a cloud save."""

    return {
        key: deepcopy(state[key]) if key in state else _MISSING
        for key in _PROJECT_SAVE_BASELINE_KEYS
    }


def restore_project_save_baseline(state: MutableMapping[str, Any], baseline: dict[str, Any]) -> None:
    """Restore the pre-save state after persistence fails."""

    for key in _PROJECT_SAVE_BASELINE_KEYS:
        value = baseline.get(key, _MISSING)
        if value is _MISSING:
            state.pop(key, None)
        else:
            state[key] = deepcopy(value)
