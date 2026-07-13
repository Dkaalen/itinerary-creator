"""Keep active workflow and calculator names aligned after a cloud rename."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from typing import Any

from app_modules.calculator_session_state import store_calculator_state
from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY
from calculator.calculator_state import CalculatorState


def apply_active_project_rename(state: MutableMapping[str, Any], result: Mapping[str, Any]) -> None:
    """Apply a successful rename to every active in-memory name boundary."""

    name = " ".join(str(result.get("name") or "").split())
    payload = result.get("payload")
    if not name or not isinstance(payload, Mapping):
        raise ValueError("A renamed project result requires a name and payload.")

    state["itinerary_name"] = name
    # The project browser is rendered before this widget on the input page, so
    # synchronising it here is safe and avoids the old name returning on rerun.
    state["itinerary_name_input"] = name
    state["active_saved_project"] = deepcopy(dict(payload))

    calculator_state = state.get(CALCULATOR_STATE_KEY)
    if isinstance(calculator_state, CalculatorState):
        store_calculator_state(
            state,
            calculator_state.with_itinerary_name(name),
            sync_name_input=True,
        )
