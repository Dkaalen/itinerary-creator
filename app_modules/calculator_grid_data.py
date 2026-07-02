"""Data conversion for the calculator grid editor."""

from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from calculator.calculations import calculate_row
from calculator.row_model import ADVANCED_FIELD_KEYS, BASIC_FIELD_KEYS, FORMULA_FIELD_KEYS, CalculatorRow

_ROW_FIELDS = {field.name for field in fields(CalculatorRow)}
_NUMERIC_FIELDS = {
    "gross_price_per_unit",
    "units",
    "supplier_commission",
    "sales_price_per_unit",
    "vat25",
    "vat15",
    "vat12",
    "vat0_domestic",
    "vat0_international",
}
_BOOLEAN_FIELDS = {"manual_booking", "non_refundable", "refundable"}
_OPTIONAL_NUMERIC_FIELDS = {"sales_price_per_unit"}


def rows_to_table_data(rows: Iterable[CalculatorRow], *, show_advanced: bool) -> list[dict[str, Any]]:
    """Return table-editor dictionaries for calculator rows."""

    visible_fields = visible_grid_fields(show_advanced)
    return [_row_to_table_data(row, visible_fields) for row in rows]


def table_data_to_rows(
    data: Iterable[Mapping[str, Any]],
    previous_rows: Iterable[CalculatorRow] = (),
) -> tuple[CalculatorRow, ...]:
    """Convert edited table dictionaries back into calculator rows."""

    previous_by_id = {row.row_id: row for row in previous_rows}
    rows: list[CalculatorRow] = []
    for index, item in enumerate(data, start=1):
        row_id = _text_value(item.get("row_id")) or str(index)
        base_row = previous_by_id.get(row_id, CalculatorRow(row_id=row_id))
        values = {field.name: getattr(base_row, field.name) for field in fields(CalculatorRow)}
        for field_name in _ROW_FIELDS.intersection(item.keys()):
            values[field_name] = _field_value(field_name, item.get(field_name))
        if not values.get("row_id"):
            values["row_id"] = row_id
        rows.append(CalculatorRow(**values))
    return tuple(rows)


def visible_grid_fields(show_advanced: bool) -> tuple[str, ...]:
    """Return visible calculator grid fields in UI order."""

    advanced = ADVANCED_FIELD_KEYS if show_advanced else ()
    return (*BASIC_FIELD_KEYS, *advanced, *FORMULA_FIELD_KEYS)


def _row_to_table_data(row: CalculatorRow, visible_fields: Iterable[str]) -> dict[str, Any]:
    calculated = calculate_row(row)
    data: dict[str, Any] = {}
    for field_name in visible_fields:
        if field_name in FORMULA_FIELD_KEYS:
            data[field_name] = getattr(calculated, field_name)
        else:
            data[field_name] = getattr(row, field_name)
    return data


def _field_value(field_name: str, value: Any) -> Any:
    if field_name in _BOOLEAN_FIELDS:
        return _bool_value(value)
    if field_name in _OPTIONAL_NUMERIC_FIELDS:
        return _optional_number_value(value)
    if field_name in _NUMERIC_FIELDS:
        return _number_value(value)
    return _text_value(value)


def _text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value).strip()


def _number_value(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _optional_number_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return _number_value(value)


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "checked"}
