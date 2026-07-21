"""Canonical restoration authority for Calculator workspace state."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.calculator_session_state import store_calculator_state
from app_modules.calculator_state_keys import CURRENCY_RATES_STATE_KEY
from calculator.calculator_state import CalculatorState

_CURRENCY_RATE_WIDGET_PREFIX = "calculator_currency_rate_"
_PRESERVE_CURRENCY_RATES = object()


def restore_calculator_workspace(
    state: MutableMapping[str, Any],
    calculator_state: CalculatorState,
    *,
    currency_rates: Mapping[str, float] | object = _PRESERVE_CURRENCY_RATES,
    sync_name_input: bool = False,
    clear_ready_download: bool = True,
) -> CalculatorState:
    """Replace the active Calculator workspace through one state authority.

    Saved projects, local workbook/backup imports, and browser recovery actions
    all converge here. Currency rates are replaced only when explicitly
    supplied; browser recovery therefore preserves the currently active rates.
    """

    if currency_rates is not _PRESERVE_CURRENCY_RATES:
        _replace_currency_rates(state, currency_rates)
    store_calculator_state(
        state,
        calculator_state,
        clear_ready_download=clear_ready_download,
        sync_name_input=sync_name_input,
    )
    return calculator_state


def _replace_currency_rates(state: MutableMapping[str, Any], rates: object) -> None:
    normalized: dict[str, float] = {}
    if isinstance(rates, Mapping):
        for code, value in rates.items():
            clean_code = str(code or "").strip().upper()
            if not clean_code:
                continue
            normalized[clean_code] = float(value)

    for key in tuple(state.keys()):
        if str(key).startswith(_CURRENCY_RATE_WIDGET_PREFIX):
            state.pop(key, None)
    state[CURRENCY_RATES_STATE_KEY] = normalized
    for code, value in normalized.items():
        state[f"{_CURRENCY_RATE_WIDGET_PREFIX}{code}"] = value


__all__ = ["restore_calculator_workspace"]
