"""Persist active saved-project current snapshots from workflow state."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.project_identity import set_active_project_id
from app_modules.saved_project_builder import Clock
from app_modules.saved_project_model import SavedItineraryProject
from app_modules.saved_project_serialization import saved_project_from_dict, saved_project_to_dict
from app_modules.saved_project_update import update_saved_project_current_snapshot
from app_modules.session_state_keys import ACTIVE_SAVED_PROJECT_KEY, ITINERARY_NAME_KEY


def refresh_active_saved_project_current_snapshot(
    state: MutableMapping[str, Any],
    *,
    clock: Clock | None = None,
) -> bool:
    """Update the active saved project from committed workflow state when present."""

    project = active_saved_project_from_state(state)
    if project is None:
        return False

    updated = update_saved_project_current_snapshot(project, state, clock=clock)
    payload = saved_project_to_dict(updated)
    state[ACTIVE_SAVED_PROJECT_KEY] = payload
    set_active_project_id(state, updated.metadata.project_id)
    state[ITINERARY_NAME_KEY] = updated.metadata.itinerary_name
    return True


def active_saved_project_from_state(state: Mapping[str, Any]) -> SavedItineraryProject | None:
    """Return the active saved project contract, or None for unsaved itineraries."""

    payload = state.get(ACTIVE_SAVED_PROJECT_KEY)
    if not isinstance(payload, Mapping):
        return None
    return saved_project_from_dict(dict(payload))
