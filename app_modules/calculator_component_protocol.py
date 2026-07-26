"""Revision-safe protocol between the Calculator browser grid and Streamlit."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

from calculator.state_revision import calculator_state_revision
from app_modules.calculator_component_result import CalculatorGridResult
from app_modules.calculator_state_keys import (
    CALCULATOR_COMPONENT_ACK_KEY,
    CALCULATOR_PROCESSED_REQUEST_IDS_KEY,
)
from calculator.calculator_state import CalculatorState

_MAX_PROCESSED_REQUESTS = 32


@dataclass(frozen=True)
class CalculatorComponentDecision:
    """Decision for one browser action before it can mutate backend state."""

    should_process: bool
    duplicate: bool
    status: str
    message: str
    current_revision: str


def authorize_calculator_grid_result(
    session_state: MutableMapping[str, Any],
    result: CalculatorGridResult,
    current_state: CalculatorState,
) -> CalculatorComponentDecision:
    """Reject stale or replayed component actions before applying their rows."""

    current_revision = calculator_state_revision(current_state)
    request_id = str(result.request_id or "").strip()
    if request_id and request_id in _processed_request_ids(session_state):
        return CalculatorComponentDecision(
            should_process=False,
            duplicate=True,
            status="duplicate",
            message="This Calculator action was already processed.",
            current_revision=current_revision,
        )

    client_revision = str(result.client_state_revision or "").strip()
    if client_revision != current_revision:
        message = (
            "The Calculator changed after this browser action started. "
            "The older action was not applied; review the current rows and try again."
        )
        acknowledge_calculator_grid_result(
            session_state,
            result,
            status="rejected_stale",
            message=message,
            server_state=current_state,
        )
        return CalculatorComponentDecision(
            should_process=False,
            duplicate=False,
            status="rejected_stale",
            message=message,
            current_revision=current_revision,
        )

    return CalculatorComponentDecision(
        should_process=True,
        duplicate=False,
        status="accepted",
        message="",
        current_revision=current_revision,
    )


def acknowledge_calculator_grid_result(
    session_state: MutableMapping[str, Any],
    result: CalculatorGridResult,
    *,
    status: str,
    message: str = "",
    server_state: CalculatorState,
) -> None:
    """Store an idempotent acknowledgement for the matching browser request."""

    request_id = str(result.request_id or "").strip()
    if not request_id:
        return
    _remember_processed_request(session_state, request_id)
    session_state[CALCULATOR_COMPONENT_ACK_KEY] = {
        "request_id": request_id,
        "action": result.action,
        "status": str(status or "accepted"),
        "message": str(message or ""),
        "server_state_revision": calculator_state_revision(server_state),
    }


def calculator_component_ack_payload(session_state: MutableMapping[str, Any]) -> dict[str, Any]:
    """Return the latest acknowledgement without consuming it.

    Acknowledgements remain available across the rerun that was triggered by a
    component value. Browser request ids make old acknowledgements harmless.
    """

    value = session_state.get(CALCULATOR_COMPONENT_ACK_KEY)
    return dict(value) if isinstance(value, dict) else {}


def clear_calculator_component_protocol_state(session_state: MutableMapping[str, Any]) -> None:
    """Forget request history at a hard Calculator project boundary."""

    session_state.pop(CALCULATOR_COMPONENT_ACK_KEY, None)
    session_state.pop(CALCULATOR_PROCESSED_REQUEST_IDS_KEY, None)


def _processed_request_ids(session_state: MutableMapping[str, Any]) -> tuple[str, ...]:
    raw = session_state.get(CALCULATOR_PROCESSED_REQUEST_IDS_KEY)
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(str(value) for value in raw if str(value).strip())


def _remember_processed_request(session_state: MutableMapping[str, Any], request_id: str) -> None:
    existing = [value for value in _processed_request_ids(session_state) if value != request_id]
    session_state[CALCULATOR_PROCESSED_REQUEST_IDS_KEY] = [request_id, *existing][:_MAX_PROCESSED_REQUESTS]


__all__ = [
    "CalculatorComponentDecision",
    "acknowledge_calculator_grid_result",
    "authorize_calculator_grid_result",
    "calculator_component_ack_payload",
    "clear_calculator_component_protocol_state",
]
