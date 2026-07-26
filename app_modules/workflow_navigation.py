"""Application route and workflow-stage transitions.

This module owns only visible navigation state. It does not reconstruct projects,
mutate Calculator data, project images, or invalidate render artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.route_registry import EDIT_STAGE, EXPORT_STAGE, INPUT_STAGE, PICTURES_STAGE
from app_modules.session_state_keys import (
    ACTIVE_APP_PAGE_KEY,
    APP_STAGE_KEY,
    CALCULATOR_PAGE,
    LOCAL_LIBRARY_PAGE,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    WORKFLOW_PAGE,
    WORKFLOW_STAGES,
)
from ui.picture_workflow import pictures_are_added


def normalize_workflow_stage(stage: object) -> str:
    """Return one supported workflow stage, falling back to input."""

    value = str(stage or INPUT_STAGE)
    return value if value in WORKFLOW_STAGES else INPUT_STAGE


def route_to_calculator(state: MutableMapping[str, Any]) -> None:
    state[ACTIVE_APP_PAGE_KEY] = CALCULATOR_PAGE


def route_to_local_library(state: MutableMapping[str, Any]) -> None:
    state[ACTIVE_APP_PAGE_KEY] = LOCAL_LIBRARY_PAGE


def route_to_workflow(state: MutableMapping[str, Any]) -> None:
    state[ACTIVE_APP_PAGE_KEY] = WORKFLOW_PAGE


def transition_workflow_stage(state: MutableMapping[str, Any], stage: object) -> str:
    """Persist and return a normalized workflow stage."""

    normalized = normalize_workflow_stage(stage)
    state[APP_STAGE_KEY] = normalized
    return normalized


def session_stage_from_state(state: Mapping[str, Any]) -> str:
    """Resolve the visible workflow stage from current project state."""

    stage = normalize_workflow_stage(state.get(APP_STAGE_KEY, INPUT_STAGE))
    if not state.get(PARSED_ROWS_KEY):
        return INPUT_STAGE
    if stage in {PICTURES_STAGE, EXPORT_STAGE} and not pictures_are_added(state.get(OUTPUT_EDITS_KEY, {}) or {}):
        return EDIT_STAGE
    return stage


__all__ = [
    "normalize_workflow_stage",
    "route_to_calculator",
    "route_to_local_library",
    "route_to_workflow",
    "session_stage_from_state",
    "transition_workflow_stage",
]
