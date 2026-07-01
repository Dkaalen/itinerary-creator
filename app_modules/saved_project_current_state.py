"""Persist active saved-project current snapshots from workflow state."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.saved_project_builder import Clock
from app_modules.saved_project_model import SavedItineraryProject
from app_modules.saved_project_serialization import saved_project_from_dict, saved_project_to_dict
from app_modules.saved_project_update import update_saved_project_current_snapshot


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
    state["active_saved_project"] = payload
    state["active_saved_project_id"] = updated.metadata.project_id
    state["itinerary_name"] = updated.metadata.itinerary_name
    return True


def active_saved_project_from_state(state: Mapping[str, Any]) -> SavedItineraryProject | None:
    """Return the active saved project contract, or None for unsaved itineraries."""

    payload = state.get("active_saved_project")
    if not isinstance(payload, Mapping):
        return None
    return saved_project_from_dict(dict(payload))
