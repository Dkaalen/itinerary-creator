"""Serialize and migrate calculator state for backup and project persistence."""

from __future__ import annotations

import json
from dataclasses import fields
from math import isfinite
from typing import Any, Mapping

from calculator.calculator_state import CalculatorState, add_row, create_calculator_state
from calculator.date_links import initialize_date_relationships
from calculator.row_model import CalculatorRow

CALCULATOR_BACKUP_SCHEMA_VERSION = 4
SUPPORTED_CALCULATOR_BACKUP_SCHEMA_VERSIONS = frozenset({1, 2, 3, 4})
_ROW_FIELD_NAMES = {field.name for field in fields(CalculatorRow)}


def calculator_state_to_dict(state: CalculatorState) -> dict[str, Any]:
    """Return a current, versioned JSON-safe calculator payload."""

    return {
        "schema_version": CALCULATOR_BACKUP_SCHEMA_VERSION,
        "kind": "booknordics_calculator_state",
        "itinerary_name": state.itinerary_name,
        "number_of_pax": state.number_of_pax,
        "trip_start_date": state.trip_start_date,
        "rows": [_row_to_dict(row) for row in state.rows],
    }


def calculator_state_to_json(state: CalculatorState) -> str:
    """Return a versioned JSON backup string for calculator state."""

    return json.dumps(
        calculator_state_to_dict(state),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )


def calculator_state_from_dict(payload: Mapping[str, Any]) -> CalculatorState:
    """Build current calculator state from a supported backup payload."""

    try:
        source_version = int(payload.get("schema_version") or 1)
    except (TypeError, ValueError):
        source_version = 1
    migrated = migrate_calculator_state_payload(payload)
    state = create_calculator_state(str(migrated.get("itinerary_name") or ""))
    state = state.with_number_of_pax(_optional_positive_int(migrated.get("number_of_pax")))
    state = state.with_trip_start_date(str(migrated.get("trip_start_date") or ""))
    rows_payload = migrated.get("rows") or []
    if not isinstance(rows_payload, list):
        raise ValueError("Calculator backup rows must be a list.")

    for row_payload in rows_payload:
        if not isinstance(row_payload, Mapping):
            continue
        state = add_row(state, _row_from_dict(row_payload))
    if source_version >= CALCULATOR_BACKUP_SCHEMA_VERSION:
        return state
    trip_start_date, rows = initialize_date_relationships(state.rows, state.trip_start_date)
    return CalculatorState(
        itinerary_name=state.itinerary_name,
        number_of_pax=state.number_of_pax,
        trip_start_date=trip_start_date,
        rows=rows,
    )


def calculator_state_from_json(payload_json: str | bytes) -> CalculatorState:
    """Build calculator state from a JSON backup string."""

    text = payload_json.decode("utf-8") if isinstance(payload_json, bytes) else str(payload_json)
    payload = json.loads(text)
    if not isinstance(payload, Mapping):
        raise ValueError("Calculator backup JSON must contain an object.")
    return calculator_state_from_dict(payload)


def migrate_calculator_state_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Migrate one historical calculator payload to the current schema."""

    if not isinstance(payload, Mapping):
        raise ValueError("Calculator backup must contain an object.")
    if payload.get("kind") not in {None, "booknordics_calculator_state"}:
        raise ValueError("Unsupported calculator backup kind.")
    try:
        version = int(payload.get("schema_version") or 1)
    except (TypeError, ValueError) as error:
        raise ValueError("Calculator backup schema version must be an integer.") from error
    if version not in SUPPORTED_CALCULATOR_BACKUP_SCHEMA_VERSIONS:
        raise ValueError(f"Unsupported calculator backup schema version: {version}.")

    migrated = dict(payload)
    if version == 1:
        migrated["number_of_pax"] = None
        version = 2
    if version == 2:
        rows = migrated.get("rows")
        if isinstance(rows, list):
            migrated["rows"] = [
                {
                    **dict(row),
                    "library_id": str(row.get("library_id") or ""),
                    "source_workbook": str(row.get("source_workbook") or ""),
                    "source_sheet": str(row.get("source_sheet") or ""),
                    "source_row": row.get("source_row"),
                }
                if isinstance(row, Mapping) else row
                for row in rows
            ]
        version = 3
    if version == 3:
        migrated["trip_start_date"] = str(migrated.get("trip_start_date") or "")
        rows = migrated.get("rows")
        if isinstance(rows, list):
            migrated["rows"] = [
                {
                    **dict(row),
                    "from_date_mode": str(row.get("from_date_mode") or ""),
                    "from_date_offset": row.get("from_date_offset"),
                    "to_date_mode": str(row.get("to_date_mode") or ""),
                    "to_date_offset": row.get("to_date_offset"),
                }
                if isinstance(row, Mapping) else row
                for row in rows
            ]
    migrated["schema_version"] = 4
    return migrated


def _row_to_dict(row: CalculatorRow) -> dict[str, Any]:
    payload = {field_name: getattr(row, field_name) for field_name in _ROW_FIELD_NAMES}
    for mode_field, offset_field in (
        ("from_date_mode", "from_date_offset"),
        ("to_date_mode", "to_date_offset"),
    ):
        if not payload.get(mode_field) and payload.get(offset_field) is None:
            payload.pop(mode_field, None)
            payload.pop(offset_field, None)
    return payload


def _row_from_dict(payload: Mapping[str, Any]) -> CalculatorRow:
    values = {
        field_name: payload.get(field_name)
        for field_name in _ROW_FIELD_NAMES
        if field_name in payload
    }
    return CalculatorRow(**values)


def _optional_positive_int(value: Any) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    if isinstance(value, bool):
        raise ValueError("Calculator number_of_pax must be a positive integer or blank.")
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError) as error:
        raise ValueError("Calculator number_of_pax must be a positive integer or blank.") from error
    if not isfinite(number) or number <= 0 or not number.is_integer():
        raise ValueError("Calculator number_of_pax must be a positive integer or blank.")
    return int(number)
