"""Calculator snapshot support for saved itinerary projects."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.calculator_currency_controls import CURRENCY_RATES_STATE_KEY
from app_modules.calculator_session_state import store_calculator_state
from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY
from calculator.calculator_state import CalculatorState, create_calculator_state
from calculator.currency_rates import normalize_currency_rates
from calculator.state_serialization import calculator_state_from_dict, calculator_state_to_dict

CALCULATOR_SNAPSHOT_KIND = "booknordics_calculator_state"
CALCULATOR_SNAPSHOT_SCHEMA_VERSION = 1


def calculator_snapshot_from_workflow_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a durable calculator snapshot for a saved project."""

    calculator_state = state.get(CALCULATOR_STATE_KEY)
    if isinstance(calculator_state, CalculatorState):
        payload = calculator_state_to_dict(calculator_state)
    else:
        payload = calculator_state_to_dict(create_calculator_state(str(state.get("itinerary_name") or "")))

    payload["currency_rates"] = normalize_currency_rates(state.get(CURRENCY_RATES_STATE_KEY))
    return normalize_calculator_snapshot(payload)


def normalize_calculator_snapshot(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe calculator snapshot with stable optional fields."""

    raw = dict(payload or {})
    rows = raw.get("rows") if isinstance(raw.get("rows"), list) else []
    return {
        "schema_version": int(raw.get("schema_version") or CALCULATOR_SNAPSHOT_SCHEMA_VERSION),
        "kind": str(raw.get("kind") or CALCULATOR_SNAPSHOT_KIND),
        "itinerary_name": str(raw.get("itinerary_name") or ""),
        "rows": [dict(row) for row in rows if isinstance(row, Mapping)],
        "currency_rates": normalize_currency_rates(raw.get("currency_rates")),
    }


def calculator_state_from_snapshot(payload: Mapping[str, Any] | None) -> CalculatorState:
    """Build calculator state from a saved-project calculator snapshot."""

    snapshot = normalize_calculator_snapshot(payload)
    return calculator_state_from_dict(snapshot)


def apply_calculator_snapshot_to_state(state: MutableMapping[str, Any], payload: Mapping[str, Any] | None) -> None:
    """Restore saved calculator state into Streamlit session-like state."""

    snapshot = normalize_calculator_snapshot(payload)
    calculator_state = calculator_state_from_snapshot(snapshot)
    store_calculator_state(state, calculator_state)
    state[CURRENCY_RATES_STATE_KEY] = normalize_currency_rates(snapshot.get("currency_rates"))


def calculator_snapshot_has_rows(payload: Mapping[str, Any] | None) -> bool:
    """Return True when the saved calculator snapshot contains user rows."""

    snapshot = normalize_calculator_snapshot(payload)
    return any(_row_has_user_content(row) for row in snapshot.get("rows", []))


def _row_has_user_content(row: Mapping[str, Any]) -> bool:
    ignored = {"row_id", "supplier_currency", "sales_currency"}
    for key, value in row.items():
        if key in ignored or str(key).endswith("_override"):
            continue
        if isinstance(value, bool):
            if value:
                return True
            continue
        if value in (None, ""):
            continue
        if str(value).strip() not in {"", "0", "0.0"}:
            return True
    return False
