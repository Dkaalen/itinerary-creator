"""Create the generated-baseline saved project after named generation."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.itinerary_name_state import itinerary_name_from_state
from app_modules.project_identity import clear_active_project_id, ensure_active_project_id
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_serialization import saved_project_to_dict
from app_modules.session_state_keys import ACTIVE_SAVED_PROJECT_KEY, ITINERARY_NAME_KEY


def create_generated_baseline_project_if_named(state: MutableMapping[str, Any]) -> bool:
    """Store a baseline saved-project contract when generation has a name."""

    itinerary_name = itinerary_name_from_state(state)
    state[ITINERARY_NAME_KEY] = itinerary_name
    if not itinerary_name:
        state.pop(ACTIVE_SAVED_PROJECT_KEY, None)
        clear_active_project_id(state)
        return False

    project_id = ensure_active_project_id(state)
    project = build_saved_project_from_state(state, itinerary_name=itinerary_name, project_id=project_id)
    state[ACTIVE_SAVED_PROJECT_KEY] = saved_project_to_dict(project)
    ensure_active_project_id(state, project_id=project.metadata.project_id)
    return True
