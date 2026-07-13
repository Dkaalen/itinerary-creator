"""Capture and restore project identity/baseline around fallible cloud saves."""

from __future__ import annotations

from collections.abc import MutableMapping
from copy import deepcopy
from typing import Any

_PROJECT_SAVE_BASELINE_KEYS = (
    "active_saved_project",
    "active_project_storage_id",
    "active_saved_project_id",
    "itinerary_name",
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
