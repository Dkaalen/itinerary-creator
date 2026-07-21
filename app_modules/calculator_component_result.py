"""Parse calculator grid component actions into backend state."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from app_modules.calculator_grid_data import table_data_to_rows
from calculator.calculator_state import CalculatorState


@dataclass(frozen=True)
class CalculatorGridResult:
    """One user action returned from the browser-side calculator grid."""

    action: str
    state: CalculatorState
    show_advanced: bool = False
    client_state_revision: str = ""
    request_id: str = ""
    upload_filename: str = ""
    upload_content_base64: str = ""


_VALID_ACTIONS = {
    "close",
    "download",
    "generate_agent",
    "generate_customer",
    "open_library",
    "open_excel",
    "sync",
}


def parse_calculator_grid_result(raw_result: object, itinerary_name: str) -> CalculatorGridResult | None:
    """Return a parsed grid result, or None when the component has no action."""

    if raw_result in (None, ""):
        return None
    data = _json_object(raw_result)
    if not data:
        return None
    action = str(data.get("action") or "sync")
    if action not in _VALID_ACTIONS:
        return None
    rows = table_data_to_rows(data.get("rows") or (), ())
    return CalculatorGridResult(
        action=action,
        state=CalculatorState(
            itinerary_name=itinerary_name,
            number_of_pax=_optional_positive_int(data.get("number_of_pax")),
            rows=rows,
        ),
        show_advanced=bool(data.get("show_advanced")),
        client_state_revision=str(data.get("client_state_revision") or ""),
        request_id=str(data.get("request_id") or ""),
        upload_filename=str(data.get("upload_filename") or ""),
        upload_content_base64=str(data.get("upload_content_base64") or ""),
    )


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


def _optional_positive_int(value: object) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
