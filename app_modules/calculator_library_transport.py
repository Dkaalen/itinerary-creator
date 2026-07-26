"""Transport handshake for retaining unchanged Local Library rows in the browser."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
import json
from typing import Any

from app_modules.calculator_state_keys import CALCULATOR_LIBRARY_BROWSER_ACK_KEY

_RETAINED_STATUS = "retained"
_CACHE_MISS_STATUS = "cache_miss"
_VALID_STATUSES = frozenset({_RETAINED_STATUS, _CACHE_MISS_STATUS})


@dataclass(frozen=True)
class CalculatorLibraryTransportSignal:
    """One browser report about its retained Local Library payload."""

    status: str
    fingerprint: str
    payload_version: str
    row_count: int


@dataclass(frozen=True)
class CalculatorLibraryTransportUpdate:
    """Result of applying one browser retention report."""

    changed: bool
    status: str


def parse_calculator_library_transport_signal(raw_result: object) -> CalculatorLibraryTransportSignal | None:
    """Parse a browser library-retention signal without treating it as a grid action."""

    data = _json_object(raw_result)
    if not isinstance(data, Mapping) or str(data.get("action") or "") != "library_transport":
        return None
    raw_signal = data.get("library_transport")
    if not isinstance(raw_signal, Mapping):
        return None
    status = str(raw_signal.get("status") or "").strip()
    if status not in _VALID_STATUSES:
        return None
    row_count = _non_negative_int(raw_signal.get("row_count"))
    if row_count is None:
        return None
    return CalculatorLibraryTransportSignal(
        status=status,
        fingerprint=str(raw_signal.get("fingerprint") or "").strip(),
        payload_version=str(raw_signal.get("payload_version") or "").strip(),
        row_count=row_count,
    )


def apply_calculator_library_transport_signal(
    session_state: MutableMapping[str, Any],
    signal: CalculatorLibraryTransportSignal,
    *,
    expected_fingerprint: str,
    expected_payload_version: str,
    expected_row_count: int,
) -> CalculatorLibraryTransportUpdate:
    """Record only signals for the exact payload contract currently rendered."""

    current = calculator_library_browser_ack(session_state)
    matching = _signal_matches(
        signal,
        expected_fingerprint=expected_fingerprint,
        expected_payload_version=expected_payload_version,
        expected_row_count=expected_row_count,
    )
    if signal.status == _CACHE_MISS_STATUS:
        if not matching:
            return CalculatorLibraryTransportUpdate(False, "ignored_stale_miss")
        changed = bool(current)
        session_state.pop(CALCULATOR_LIBRARY_BROWSER_ACK_KEY, None)
        return CalculatorLibraryTransportUpdate(changed, _CACHE_MISS_STATUS)

    if not matching:
        return CalculatorLibraryTransportUpdate(False, "ignored_stale_ack")

    acknowledged = {
        "fingerprint": signal.fingerprint,
        "payload_version": signal.payload_version,
        "row_count": signal.row_count,
    }
    changed = current != acknowledged
    session_state[CALCULATOR_LIBRARY_BROWSER_ACK_KEY] = acknowledged
    return CalculatorLibraryTransportUpdate(changed, _RETAINED_STATUS)


def _signal_matches(
    signal: CalculatorLibraryTransportSignal,
    *,
    expected_fingerprint: str,
    expected_payload_version: str,
    expected_row_count: int,
) -> bool:
    return (
        signal.fingerprint == str(expected_fingerprint or "")
        and signal.payload_version == str(expected_payload_version or "")
        and signal.row_count == int(expected_row_count or 0)
    )


def apply_calculator_library_transport_result(
    session_state: MutableMapping[str, Any],
    raw_result: object,
    payload: Mapping[str, Any],
) -> CalculatorLibraryTransportUpdate | None:
    """Parse and apply one component transport message for the rendered payload."""

    signal = parse_calculator_library_transport_signal(raw_result)
    if signal is None:
        return None
    return apply_calculator_library_transport_signal(
        session_state,
        signal,
        expected_fingerprint=str(payload.get("library_fingerprint") or ""),
        expected_payload_version=str(payload.get("library_payload_version") or ""),
        expected_row_count=int(payload.get("library_row_count") or 0),
    )


def calculator_library_browser_ack(session_state: Mapping[str, Any]) -> dict[str, Any]:
    value = session_state.get(CALCULATOR_LIBRARY_BROWSER_ACK_KEY)
    if not isinstance(value, Mapping):
        return {}
    try:
        row_count = int(value.get("row_count") or 0)
    except (TypeError, ValueError):
        return {}
    if row_count < 0:
        return {}
    return {
        "fingerprint": str(value.get("fingerprint") or ""),
        "payload_version": str(value.get("payload_version") or ""),
        "row_count": row_count,
    }


def calculator_library_rows_are_acknowledged(
    browser_ack: Mapping[str, Any] | None,
    *,
    fingerprint: str,
    payload_version: str,
    row_count: int,
) -> bool:
    ack = dict(browser_ack or {})
    return (
        str(ack.get("fingerprint") or "") == str(fingerprint or "")
        and str(ack.get("payload_version") or "") == str(payload_version or "")
        and _non_negative_int(ack.get("row_count")) == int(row_count or 0)
    )


def clear_calculator_library_browser_ack(session_state: MutableMapping[str, Any]) -> None:
    session_state.pop(CALCULATOR_LIBRARY_BROWSER_ACK_KEY, None)


def _json_object(raw_result: object) -> dict[str, Any] | None:
    if isinstance(raw_result, dict):
        return raw_result
    if not isinstance(raw_result, str):
        return None
    try:
        parsed = json.loads(raw_result)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _non_negative_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


__all__ = [
    "CalculatorLibraryTransportSignal",
    "CalculatorLibraryTransportUpdate",
    "apply_calculator_library_transport_result",
    "apply_calculator_library_transport_signal",
    "calculator_library_browser_ack",
    "calculator_library_rows_are_acknowledged",
    "clear_calculator_library_browser_ack",
    "parse_calculator_library_transport_signal",
]
