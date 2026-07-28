"""Detect unsaved work before replacing the current itinerary workspace."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY
from app_modules.performance_telemetry import measure_timing, record_trace, telemetry_is_active
from app_modules.project_persistence_state import last_saved_project_baseline
from app_modules.project_workspace_revision import (
    current_workspace_component_signatures,
    persisted_workspace_signatures,
    workspace_revision,
)
from app_modules.saved_project_calculator_state import calculator_snapshot_has_rows
from app_modules.saved_project_cleaning import clean_output_edits, clean_parsed_rows
from app_modules.session_state_keys import (
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    RAW_TEXT_INPUT_KEY,
)
from calculator.calculator_state import CalculatorState
from calculator.state_serialization import calculator_state_to_dict


def active_project_has_unsaved_changes(
    state: Mapping[str, Any],
    *,
    calculator_state: object | None = None,
) -> bool:
    """Return whether replacing the current workspace could discard real work."""

    telemetry_state = state if isinstance(state, MutableMapping) and telemetry_is_active(state) else None
    with measure_timing(telemetry_state, "unsaved_state_check"):
        result = _active_project_has_unsaved_changes(state, calculator_state=calculator_state)
    if telemetry_state is not None:
        record_trace(
            telemetry_state,
            "unsaved_state_checked",
            result=result,
            has_saved_baseline=bool(last_saved_project_baseline(state)),
            parsed_row_count=len(state.get(PARSED_ROWS_KEY) or ()),
            workspace_revision=workspace_revision(state),
        )
    return result


def _active_project_has_unsaved_changes(
    state: Mapping[str, Any],
    *,
    calculator_state: object | None = None,
) -> bool:
    project = last_saved_project_baseline(state)
    if calculator_state is None:
        calculator_state = state.get(CALCULATOR_STATE_KEY)
    if not isinstance(project, Mapping):
        return _detached_workspace_has_content(state, calculator_state)

    current = current_workspace_component_signatures(state, calculator_state=calculator_state)
    saved = persisted_workspace_signatures(state, project)

    if current.get("name") and current.get("name") != saved.get("name"):
        return True
    if current.get("parsed_present") and current.get("parsed_rows") != saved.get("parsed_rows"):
        return True
    if current.get("output_present") and current.get("output_edits") != saved.get("output_edits"):
        return True
    if current.get("detail_present") and current.get("detail_level") != saved.get("detail_level"):
        return True
    if current.get("layout_present") and current.get("day_page_layout") != saved.get("day_page_layout"):
        return True
    if current.get("source_present") and current.get("source_input") != saved.get("source_input"):
        return True

    if not current.get("calculator_present"):
        return False
    if not saved.get("calculator_present"):
        return bool(current.get("calculator_has_rows"))
    if current.get("calculator") != saved.get("calculator"):
        return True
    if current.get("rates_present") and saved.get("rates_present"):
        return current.get("rates") != saved.get("rates")
    return False


def _detached_workspace_has_content(state: Mapping[str, Any], calculator_state: object) -> bool:
    """Return whether a workspace without a saved-project baseline contains real work."""

    if _clean_name(state.get(ITINERARY_NAME_KEY) or state.get(ITINERARY_NAME_INPUT_KEY)):
        return True
    if str(state.get(RAW_TEXT_INPUT_KEY) or "").strip():
        return True
    if clean_parsed_rows(state.get(PARSED_ROWS_KEY) or []):
        return True
    output_edits = state.get(OUTPUT_EDITS_KEY)
    if isinstance(output_edits, Mapping) and bool(clean_output_edits(output_edits)):
        return True
    if not isinstance(calculator_state, CalculatorState):
        return False
    return calculator_snapshot_has_rows(calculator_state_to_dict(calculator_state))


def _clean_name(value: object) -> str:
    return " ".join(str(value or "").split())
