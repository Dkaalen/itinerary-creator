"""Detect unsaved calculator changes for the active cloud project."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY, CURRENCY_RATES_STATE_KEY
from calculator.calculator_state import CalculatorState
from calculator.currency_rates import normalize_currency_rates
from calculator.state_serialization import calculator_state_to_dict
from app_modules.session_state_keys import ACTIVE_SAVED_PROJECT_KEY, ITINERARY_NAME_INPUT_KEY, ITINERARY_NAME_KEY


def active_project_has_unsaved_changes(state: Mapping[str, Any]) -> bool:
    """Return whether the current calculator/name differs from the saved snapshot."""

    project = state.get(ACTIVE_SAVED_PROJECT_KEY)
    if not isinstance(project, Mapping):
        return False
    metadata = project.get("metadata") if isinstance(project.get("metadata"), Mapping) else {}
    saved_name = _clean_name(metadata.get("itinerary_name"))
    current_name = _clean_name(state.get(ITINERARY_NAME_KEY) or state.get(ITINERARY_NAME_INPUT_KEY))
    if current_name and current_name != saved_name:
        return True

    calculator_state = state.get(CALCULATOR_STATE_KEY)
    if not isinstance(calculator_state, CalculatorState):
        return False
    saved_calculator = project.get("calculator_snapshot")
    if not isinstance(saved_calculator, Mapping):
        return bool(calculator_state.rows)
    if _calculator_signature(calculator_state_to_dict(calculator_state)) != _calculator_signature(saved_calculator):
        return True
    current_rates = state.get(CURRENCY_RATES_STATE_KEY)
    saved_rates = saved_calculator.get("currency_rates")
    if isinstance(current_rates, Mapping) and isinstance(saved_rates, Mapping):
        return _rate_signature(current_rates) != _rate_signature(saved_rates)
    return False



def _rate_signature(rates: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    normalized = normalize_currency_rates(rates)
    return tuple(sorted((code, format(float(value), ".12g")) for code, value in normalized.items()))

def _calculator_signature(payload: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(payload.get("schema_version") or 1),
        _clean_name(payload.get("itinerary_name")),
        payload.get("number_of_pax"),
        tuple(_stable_row(row) for row in payload.get("rows") or () if isinstance(row, Mapping)),
    )


def _stable_row(row: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted((str(key), _stable_value(value)) for key, value in row.items()))


def _stable_value(value: Any) -> Any:
    if isinstance(value, float) and value == 0:
        return 0.0
    if isinstance(value, list):
        return tuple(_stable_value(item) for item in value)
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _stable_value(item)) for key, item in value.items()))
    return value


def _clean_name(value: object) -> str:
    return " ".join(str(value or "").split())
