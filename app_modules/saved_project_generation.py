"""Create the generated-baseline saved project after named generation."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.itinerary_name_state import itinerary_name_from_state
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_serialization import saved_project_to_dict

_ACTIVE_PROJECT_KEYS = ("active_saved_project", "active_saved_project_id")


def create_generated_baseline_project_if_named(state: MutableMapping[str, Any]) -> bool:
    """Store a baseline saved-project contract when generation has a name."""

    itinerary_name = itinerary_name_from_state(state)
    state["itinerary_name"] = itinerary_name
    if not itinerary_name:
        for key in _ACTIVE_PROJECT_KEYS:
            state.pop(key, None)
        return False

    project_id = str(state.get("active_project_storage_id") or "").strip() or None
    project = build_saved_project_from_state(state, itinerary_name=itinerary_name, project_id=project_id)
    state["active_saved_project"] = saved_project_to_dict(project)
    state["active_saved_project_id"] = project.metadata.project_id
    state["active_project_storage_id"] = project.metadata.project_id
    return True
