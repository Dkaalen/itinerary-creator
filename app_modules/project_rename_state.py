"""Keep active workflow and calculator names aligned after a cloud rename."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from typing import Any

from app_modules.calculator_session_state import store_calculator_state
from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY
from app_modules.project_persistence_state import mark_cloud_project_persisted
from calculator.calculator_state import CalculatorState
from app_modules.session_state_keys import (
    ACTIVE_SAVED_PROJECT_KEY,
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
)


def apply_active_project_rename(state: MutableMapping[str, Any], result: Mapping[str, Any]) -> None:
    """Apply a successful rename to every active in-memory name boundary."""

    name = " ".join(str(result.get("name") or "").split())
    payload = result.get("payload")
    if not name or not isinstance(payload, Mapping):
        raise ValueError("A renamed project result requires a name and payload.")

    state[ITINERARY_NAME_KEY] = name
    # The project browser is rendered before this widget on the input page, so
    # synchronising it here is safe and avoids the old name returning on rerun.
    state[ITINERARY_NAME_INPUT_KEY] = name
    state[ACTIVE_SAVED_PROJECT_KEY] = deepcopy(dict(payload))
    mark_cloud_project_persisted(state, payload=payload, version_id=result.get("version_id"))

    calculator_state = state.get(CALCULATOR_STATE_KEY)
    if isinstance(calculator_state, CalculatorState):
        store_calculator_state(
            state,
            calculator_state.with_itinerary_name(name),
            sync_name_input=True,
        )
