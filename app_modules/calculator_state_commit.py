"""Neutral Calculator state-commit boundary.

Recovery and file-import code prepare validated commit requests. This module is
solely responsible for applying canonical Calculator values to application
state and does not import browser recovery, Streamlit, or project UI modules.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from math import isfinite
from typing import Any

from app_modules.calculator_state_keys import (
    CALCULATOR_ADVANCED_TOGGLE_KEY,
    CALCULATOR_DRAFT_NAMESPACE_KEY,
    CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY,
    CALCULATOR_READY_DOWNLOAD_KEY,
    CALCULATOR_STATE_KEY,
    CURRENCY_RATES_STATE_KEY,
)
from calculator.calculator_state import CalculatorState
from calculator.state_revision import calculator_state_revision
from app_modules.project_workspace_revision import mark_workspace_mutated

_CURRENCY_RATE_WIDGET_PREFIX = "calculator_currency_rate_"


@dataclass(frozen=True)
class CalculatorStateCommitRequest:
    """Validated Calculator values awaiting an atomic application-state commit."""

    state: CalculatorState
    source: str
    currency_rates: Mapping[str, float] = field(default_factory=dict)
    replace_currency_rates: bool = False
    expected_revision: str = ""
    project_identity: str = ""
    show_advanced: bool | None = None
    sync_name_input: bool = False
    clear_ready_download: bool = True


@dataclass(frozen=True)
class CalculatorStateCommitResult:
    """Accepted or rejected result of one canonical state commit."""

    accepted: bool
    changed: bool
    status: str
    source: str
    message: str
    previous_state: CalculatorState | None
    server_state: CalculatorState | None
    previous_revision: str
    server_revision: str
    project_identity: str


def commit_calculator_state(
    session_state: MutableMapping[str, Any],
    request: CalculatorStateCommitRequest,
) -> CalculatorStateCommitResult:
    """Validate guards, then atomically apply one Calculator state request."""

    if not isinstance(request.state, CalculatorState):
        raise TypeError("Calculator commit state must be CalculatorState.")

    source = _clean_text(request.source) or "unknown"
    project_identity = _clean_text(request.project_identity)
    active_project_identity = _clean_text(session_state.get(CALCULATOR_DRAFT_NAMESPACE_KEY))
    previous = session_state.get(CALCULATOR_STATE_KEY)
    previous_state = previous if isinstance(previous, CalculatorState) else None
    previous_revision = calculator_state_revision(previous_state) if previous_state is not None else ""

    if project_identity and active_project_identity and project_identity != active_project_identity:
        return CalculatorStateCommitResult(
            accepted=False,
            changed=False,
            status="rejected_project",
            source=source,
            message="Calculator recovery belonged to a different project and was not applied.",
            previous_state=previous_state,
            server_state=previous_state,
            previous_revision=previous_revision,
            server_revision=previous_revision,
            project_identity=active_project_identity,
        )

    expected_revision = _clean_text(request.expected_revision)
    if expected_revision and expected_revision != previous_revision:
        return CalculatorStateCommitResult(
            accepted=False,
            changed=False,
            status="rejected_stale",
            source=source,
            message=(
                "The Calculator changed after this recovery action started. "
                "The older state was not applied."
            ),
            previous_state=previous_state,
            server_state=previous_state,
            previous_revision=previous_revision,
            server_revision=previous_revision,
            project_identity=active_project_identity or project_identity,
        )

    normalized_rates = (
        _normalize_currency_rates(request.currency_rates)
        if request.replace_currency_rates
        else None
    )
    changed = previous_state != request.state
    previous_rates = None
    if normalized_rates is not None:
        current_rates = session_state.get(CURRENCY_RATES_STATE_KEY)
        try:
            previous_rates = _normalize_currency_rates(current_rates if isinstance(current_rates, Mapping) else {})
        except (TypeError, ValueError):
            previous_rates = {}
    rates_changed = normalized_rates is not None and previous_rates != normalized_rates

    if normalized_rates is not None:
        _replace_currency_rates(session_state, normalized_rates)
    session_state[CALCULATOR_STATE_KEY] = request.state
    if request.show_advanced is not None:
        session_state[CALCULATOR_ADVANCED_TOGGLE_KEY] = bool(request.show_advanced)
    if request.sync_name_input:
        session_state[CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY] = True
    if request.clear_ready_download and changed:
        session_state.pop(CALCULATOR_READY_DOWNLOAD_KEY, None)
    if changed or rates_changed:
        mark_workspace_mutated(session_state)

    server_revision = calculator_state_revision(request.state)
    return CalculatorStateCommitResult(
        accepted=True,
        changed=changed,
        status="accepted" if changed else "unchanged",
        source=source,
        message="",
        previous_state=previous_state,
        server_state=request.state,
        previous_revision=previous_revision,
        server_revision=server_revision,
        project_identity=active_project_identity or project_identity,
    )


def _replace_currency_rates(state: MutableMapping[str, Any], rates: Mapping[str, float]) -> None:
    for key in tuple(state.keys()):
        if str(key).startswith(_CURRENCY_RATE_WIDGET_PREFIX):
            state.pop(key, None)
    normalized = dict(rates)
    state[CURRENCY_RATES_STATE_KEY] = normalized
    for code, value in normalized.items():
        state[f"{_CURRENCY_RATE_WIDGET_PREFIX}{code}"] = value


def _normalize_currency_rates(rates: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(rates, Mapping):
        raise TypeError("Currency rates must be a mapping.")
    normalized: dict[str, float] = {}
    for code, value in rates.items():
        clean_code = _clean_text(code).upper()
        if not clean_code:
            continue
        parsed = float(value)
        if not isfinite(parsed):
            raise ValueError(f"Currency rate for {clean_code} must be finite.")
        normalized[clean_code] = parsed
    return normalized


def _clean_text(value: object) -> str:
    return str(value or "").strip()


__all__ = [
    "CalculatorStateCommitRequest",
    "CalculatorStateCommitResult",
    "commit_calculator_state",
]
