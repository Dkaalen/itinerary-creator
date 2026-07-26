"""Mutation-free preparation of Calculator workspace restoration requests."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.calculator_state_commit import (
    CalculatorStateCommitRequest,
    commit_calculator_state,
)
from calculator.calculator_state import CalculatorState

_PRESERVE_CURRENCY_RATES = object()


def calculator_workspace_commit_request(
    calculator_state: CalculatorState,
    *,
    source: str = "workspace_restore",
    currency_rates: Mapping[str, float] | object = _PRESERVE_CURRENCY_RATES,
    sync_name_input: bool = False,
    clear_ready_download: bool = True,
    expected_revision: str = "",
    project_identity: str = "",
    show_advanced: bool | None = None,
) -> CalculatorStateCommitRequest:
    """Build a neutral commit request without mutating application state."""

    replace_rates = currency_rates is not _PRESERVE_CURRENCY_RATES
    return CalculatorStateCommitRequest(
        state=calculator_state,
        source=source,
        currency_rates=dict(currency_rates) if isinstance(currency_rates, Mapping) else {},
        replace_currency_rates=replace_rates,
        expected_revision=expected_revision,
        project_identity=project_identity,
        show_advanced=show_advanced,
        sync_name_input=sync_name_input,
        clear_ready_download=clear_ready_download,
    )


def restore_calculator_workspace(
    state: MutableMapping[str, Any],
    calculator_state: CalculatorState,
    *,
    source: str = "workspace_restore",
    currency_rates: Mapping[str, float] | object = _PRESERVE_CURRENCY_RATES,
    sync_name_input: bool = False,
    clear_ready_download: bool = True,
    expected_revision: str = "",
    project_identity: str = "",
    show_advanced: bool | None = None,
) -> CalculatorState:
    """Compatibility application wrapper around the neutral commit boundary."""

    request = calculator_workspace_commit_request(
        calculator_state,
        source=source,
        currency_rates=currency_rates,
        sync_name_input=sync_name_input,
        clear_ready_download=clear_ready_download,
        expected_revision=expected_revision,
        project_identity=project_identity,
        show_advanced=show_advanced,
    )
    result = commit_calculator_state(state, request)
    return result.server_state or calculator_state


__all__ = ["calculator_workspace_commit_request", "restore_calculator_workspace"]
