"""Revision-aware signatures for saved-project dirty-state checks.

Production mutation owners increment one workspace revision. Expensive canonical
signatures are then rebuilt only once for that revision. Plain mappings without
revision ownership deliberately bypass the cache so tests and external callers
retain exact comparison semantics.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, MutableMapping
from typing import Any

from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY, CURRENCY_RATES_STATE_KEY
from app_modules.saved_project_cleaning import clean_output_edits, clean_parsed_rows
from app_modules.session_state_keys import (
    DAY_PAGE_LAYOUT_KEY,
    DETAIL_LEVEL_KEY,
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    RAW_TEXT_INPUT_KEY,
)
from calculator.calculator_state import CalculatorState
from calculator.currency_rates import normalize_currency_rates
from calculator.state_serialization import calculator_state_to_dict

WORKSPACE_REVISION_KEY = "_project_workspace_revision_v1"
WORKSPACE_SIGNATURE_CACHE_KEY = "_project_workspace_signature_cache_v1"
PERSISTED_BASELINE_SIGNATURES_KEY = "_project_persisted_baseline_signatures_v1"


def workspace_revision(state: Mapping[str, Any]) -> int:
    try:
        return max(0, int(state.get(WORKSPACE_REVISION_KEY) or 0))
    except (TypeError, ValueError):
        return 0


def mark_workspace_mutated(state: MutableMapping[str, Any]) -> int:
    """Advance the canonical mutation revision and invalidate cached signatures."""

    revision = workspace_revision(state) + 1
    state[WORKSPACE_REVISION_KEY] = revision
    state.pop(WORKSPACE_SIGNATURE_CACHE_KEY, None)
    return revision


def reset_workspace_revision(state: MutableMapping[str, Any]) -> None:
    """Start a new workspace revision boundary without carrying old signatures."""

    state[WORKSPACE_REVISION_KEY] = 0
    state.pop(WORKSPACE_SIGNATURE_CACHE_KEY, None)


def clear_workspace_revision_state(state: MutableMapping[str, Any]) -> None:
    state.pop(WORKSPACE_REVISION_KEY, None)
    state.pop(WORKSPACE_SIGNATURE_CACHE_KEY, None)
    state.pop(PERSISTED_BASELINE_SIGNATURES_KEY, None)


def current_workspace_component_signatures(
    state: Mapping[str, Any],
    *,
    calculator_state: object | None = None,
) -> dict[str, Any]:
    """Return canonical component signatures, cached only under revision ownership."""

    if calculator_state is None:
        calculator_state = state.get(CALCULATOR_STATE_KEY)
    cache_token = _current_cache_token(state, calculator_state)
    if WORKSPACE_REVISION_KEY in state and isinstance(state, MutableMapping):
        cached = state.get(WORKSPACE_SIGNATURE_CACHE_KEY)
        if isinstance(cached, Mapping) and cached.get("token") == cache_token:
            signatures = cached.get("signatures")
            if isinstance(signatures, Mapping):
                return dict(signatures)

    signatures = _build_current_signatures(state, calculator_state)
    if WORKSPACE_REVISION_KEY in state and isinstance(state, MutableMapping):
        state[WORKSPACE_SIGNATURE_CACHE_KEY] = {
            "token": cache_token,
            "signatures": dict(signatures),
        }
    return signatures


def persisted_payload_component_signatures(payload: Mapping[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    snapshot = payload.get("current_snapshot") if isinstance(payload.get("current_snapshot"), Mapping) else {}
    source = payload.get("source") if isinstance(payload.get("source"), Mapping) else {}
    calculator = payload.get("calculator_snapshot") if isinstance(payload.get("calculator_snapshot"), Mapping) else None
    rates = calculator.get("currency_rates") if isinstance(calculator, Mapping) else None
    return {
        "name": _clean_text(metadata.get("itinerary_name")),
        "parsed_rows": _digest(clean_parsed_rows(snapshot.get("parsed_rows") or [])),
        "output_edits": _digest(clean_output_edits(snapshot.get("output_edits") or {})),
        "detail_level": _clean_text(snapshot.get("detail_level")),
        "day_page_layout": _clean_text(snapshot.get("day_page_layout")),
        "source_input": _text_digest(source.get("source_input")),
        "calculator_present": isinstance(calculator, Mapping),
        "calculator": _calculator_payload_digest(calculator) if isinstance(calculator, Mapping) else "",
        "rates_present": isinstance(rates, Mapping),
        "rates": _rates_digest(rates) if isinstance(rates, Mapping) else "",
    }


def remember_persisted_workspace_signatures(
    state: MutableMapping[str, Any],
    payload: Mapping[str, Any],
) -> None:
    state[PERSISTED_BASELINE_SIGNATURES_KEY] = persisted_payload_component_signatures(payload)


def persisted_workspace_signatures(
    state: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    cached = state.get(PERSISTED_BASELINE_SIGNATURES_KEY)
    if isinstance(cached, Mapping):
        return dict(cached)
    return persisted_payload_component_signatures(payload)


def clear_persisted_workspace_signatures(state: MutableMapping[str, Any]) -> None:
    state.pop(PERSISTED_BASELINE_SIGNATURES_KEY, None)


def _build_current_signatures(state: Mapping[str, Any], calculator_state: object) -> dict[str, Any]:
    rates = state.get(CURRENCY_RATES_STATE_KEY)
    calculator_payload = (
        calculator_state_to_dict(calculator_state)
        if isinstance(calculator_state, CalculatorState)
        else None
    )
    return {
        "name": _clean_text(state.get(ITINERARY_NAME_KEY) or state.get(ITINERARY_NAME_INPUT_KEY)),
        "parsed_present": PARSED_ROWS_KEY in state,
        "parsed_rows": _digest(clean_parsed_rows(state.get(PARSED_ROWS_KEY) or [])) if PARSED_ROWS_KEY in state else "",
        "output_present": OUTPUT_EDITS_KEY in state,
        "output_edits": _digest(clean_output_edits(state.get(OUTPUT_EDITS_KEY) or {})) if OUTPUT_EDITS_KEY in state else "",
        "detail_present": DETAIL_LEVEL_KEY in state,
        "detail_level": _clean_text(state.get(DETAIL_LEVEL_KEY)),
        "layout_present": DAY_PAGE_LAYOUT_KEY in state,
        "day_page_layout": _clean_text(state.get(DAY_PAGE_LAYOUT_KEY)),
        "source_present": RAW_TEXT_INPUT_KEY in state,
        "source_input": _text_digest(state.get(RAW_TEXT_INPUT_KEY)) if RAW_TEXT_INPUT_KEY in state else "",
        "calculator_present": calculator_payload is not None,
        "calculator": _calculator_payload_digest(calculator_payload) if calculator_payload is not None else "",
        "calculator_has_rows": bool(calculator_state.rows) if isinstance(calculator_state, CalculatorState) else False,
        "rates_present": isinstance(rates, Mapping),
        "rates": _rates_digest(rates) if isinstance(rates, Mapping) else "",
    }


def _current_cache_token(state: Mapping[str, Any], calculator_state: object) -> tuple[Any, ...]:
    rates = state.get(CURRENCY_RATES_STATE_KEY)
    return (
        workspace_revision(state),
        id(state.get(PARSED_ROWS_KEY)),
        id(state.get(OUTPUT_EDITS_KEY)),
        id(calculator_state),
        id(rates),
        _clean_text(state.get(ITINERARY_NAME_KEY) or state.get(ITINERARY_NAME_INPUT_KEY)),
        state.get(RAW_TEXT_INPUT_KEY),
        _clean_text(state.get(DETAIL_LEVEL_KEY)),
        _clean_text(state.get(DAY_PAGE_LAYOUT_KEY)),
    )


def _calculator_payload_digest(payload: Mapping[str, Any]) -> str:
    compact = {
        "schema_version": int(payload.get("schema_version") or 1),
        "itinerary_name": _clean_text(payload.get("itinerary_name")),
        "number_of_pax": payload.get("number_of_pax"),
        "rows": payload.get("rows") or [],
    }
    return _digest(compact)


def _rates_digest(rates: Mapping[str, Any]) -> str:
    normalized = normalize_currency_rates(rates)
    compact = {code: format(float(value), ".12g") for code, value in sorted(normalized.items())}
    return _digest(compact)


def _text_digest(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


__all__ = [
    "PERSISTED_BASELINE_SIGNATURES_KEY",
    "WORKSPACE_REVISION_KEY",
    "WORKSPACE_SIGNATURE_CACHE_KEY",
    "clear_persisted_workspace_signatures",
    "clear_workspace_revision_state",
    "current_workspace_component_signatures",
    "mark_workspace_mutated",
    "persisted_payload_component_signatures",
    "persisted_workspace_signatures",
    "remember_persisted_workspace_signatures",
    "reset_workspace_revision",
    "workspace_revision",
]
