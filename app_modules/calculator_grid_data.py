"""Data conversion for the calculator grid editor."""

from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from calculator.calculations import calculate_row
from calculator.defaults import DEFAULT_CALCULATOR_CURRENCY
from calculator.numeric_input import optional_numeric_input, parse_numeric_input
from calculator.row_model import (
    ADVANCED_FIELD_KEYS,
    BASIC_FIELD_KEYS,
    FORMULA_FIELD_KEYS,
    FORMULA_OVERRIDE_FIELD_BY_KEY,
    FORMULA_OVERRIDE_FIELDS,
    CalculatorRow,
)

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
    *FORMULA_OVERRIDE_FIELDS,
}
_BOOLEAN_FIELDS = {"manual_booking", "non_refundable", "refundable"}
_OPTIONAL_NUMERIC_FIELDS = {"sales_price_per_unit"}
_BLANK_NUMERIC_MARKERS = {"", "none", "nan", "null"}
_DEFAULT_ONLY_TEXT_FIELDS = {"row_id", "supplier_currency", "sales_currency"}
_PERCENT_UI_FIELDS = {"supplier_commission"}


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
        for field_name, raw_value in item.items():
            if field_name in _ROW_FIELDS:
                values[field_name] = _field_value(field_name, raw_value)
                continue
            override_field = FORMULA_OVERRIDE_FIELD_BY_KEY.get(str(field_name))
            if override_field:
                values[override_field] = _formula_override_value(str(field_name), raw_value)
        if not values.get("row_id"):
            values["row_id"] = row_id
        values["supplier_currency"] = _currency_or_default(values.get("supplier_currency"))
        values["sales_currency"] = _currency_or_default(values.get("sales_currency"))
        rows.append(CalculatorRow(**values))
    return tuple(rows)


def rows_have_user_edit_changes(
    edited_rows: tuple[CalculatorRow, ...],
    current_rows: tuple[CalculatorRow, ...],
) -> bool:
    """Return whether edited grid rows changed user-editable calculator data."""

    return edited_rows != current_rows


def visible_grid_fields(show_advanced: bool) -> tuple[str, ...]:
    """Return visible calculator grid fields in UI order."""

    advanced = ADVANCED_FIELD_KEYS if show_advanced else ()
    return (*BASIC_FIELD_KEYS, *advanced, *FORMULA_FIELD_KEYS)


def _row_to_table_data(row: CalculatorRow, visible_fields: Iterable[str]) -> dict[str, Any]:
    calculated = calculate_row(row)
    row_is_blank = _row_has_no_user_values(row)
    data: dict[str, Any] = {}
    for field_name in visible_fields:
        if field_name in FORMULA_FIELD_KEYS:
            override_field = FORMULA_OVERRIDE_FIELD_BY_KEY[field_name]
            override_value = getattr(row, override_field)
            data[field_name] = None if row_is_blank and override_value is None else getattr(calculated, field_name)
            data[override_field] = override_value
            continue
        value = getattr(row, field_name)
        if field_name == "sales_price_per_unit" and value is None:
            data[field_name] = ""
            continue
        if row_is_blank and field_name in _NUMERIC_FIELDS:
            data[field_name] = None
            continue
        if field_name in _PERCENT_UI_FIELDS:
            data[field_name] = _decimal_to_percent(value)
            continue
        data[field_name] = value
    return data


def _field_value(field_name: str, value: Any) -> Any:
    if field_name in _BOOLEAN_FIELDS:
        return _bool_value(value)
    if field_name in _OPTIONAL_NUMERIC_FIELDS:
        return _optional_number_value(value)
    if field_name in _PERCENT_UI_FIELDS:
        return _percent_to_decimal(value)
    if field_name in _NUMERIC_FIELDS:
        return _number_value(value)
    return _text_value(value)


def _formula_override_value(field_name: str, value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.casefold() in _BLANK_NUMERIC_MARKERS:
        return None
    if field_name == "gp_percent":
        return _percent_to_decimal(text)
    return _number_value(text)


def _text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text = str(value).strip()
    return "" if text.casefold() in _BLANK_NUMERIC_MARKERS else text


def _number_value(value: Any) -> float:
    return parse_numeric_input(value)


def _optional_number_value(value: Any) -> float | None:
    return optional_numeric_input(value)


def _percent_to_decimal(value: Any) -> float:
    """Convert UI percentage input to the decimal value used by formulas."""

    number = _number_value(value)
    if number == 0:
        return 0.0
    return number / 100


def _decimal_to_percent(value: Any) -> float:
    """Convert formula decimal percentage to the visible grid percentage."""

    return _number_value(value) * 100


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "checked"}


def _currency_or_default(value: object) -> str:
    text = _text_value(value).upper()
    return text or DEFAULT_CALCULATOR_CURRENCY


def _row_has_no_user_values(row: CalculatorRow) -> bool:
    for field in fields(CalculatorRow):
        field_name = field.name
        if field_name in _DEFAULT_ONLY_TEXT_FIELDS:
            continue
        value = getattr(row, field_name)
        if _value_has_content(value):
            return False
    return True


def _value_has_content(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) != 0.0
    return bool(str(value or "").strip())
