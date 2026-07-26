"""Calculator lifecycle transitions across local imports and generation."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.calculator_state_keys import CALCULATOR_RETURN_AVAILABLE_KEY
from app_modules.project_session_cleanup import clear_active_cloud_project_session
from app_modules.workflow_navigation import route_to_calculator, route_to_workflow, transition_workflow_stage


def begin_local_calculator_import(state: MutableMapping[str, Any]) -> None:
    """Detach a local workbook from cloud identity while keeping Calculator active."""

    clear_active_cloud_project_session(state)
    state.pop(CALCULATOR_RETURN_AVAILABLE_KEY, None)
    route_to_calculator(state)


def complete_calculator_generation(state: MutableMapping[str, Any]) -> None:
    """Expose the generated workflow while preserving a Calculator return route."""

    state[CALCULATOR_RETURN_AVAILABLE_KEY] = True
    route_to_workflow(state)


def fail_calculator_generation(state: MutableMapping[str, Any], previous_stage: object) -> str:
    """Keep Calculator active and restore the prior valid workflow stage."""

    route_to_calculator(state)
    return transition_workflow_stage(state, previous_stage)


__all__ = [
    "begin_local_calculator_import",
    "complete_calculator_generation",
    "fail_calculator_generation",
]
