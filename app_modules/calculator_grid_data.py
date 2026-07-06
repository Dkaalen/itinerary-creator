"""Data conversion for the calculator grid editor."""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Iterable, Mapping

from app_modules.calculator_grid_values import (
    NUMERIC_FIELDS,
    PERCENT_UI_FIELDS,
    currency_or_default,
    decimal_to_percent,
    field_value,
    formula_override_value,
    number_value,
    row_has_no_user_values,
    text_value,
)
from calculator.calculations import calculate_row
from calculator.row_model import (
    ADVANCED_FIELD_KEYS,
    BASIC_FIELD_KEYS,
    FORMULA_FIELD_KEYS,
    FORMULA_OVERRIDE_FIELD_BY_KEY,
    CalculatorRow,
)

_ROW_FIELDS = {field.name for field in fields(CalculatorRow)}


def rows_to_table_data(
    rows: Iterable[CalculatorRow],
    *,
    show_advanced: bool,
    currency_rates: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Return table-editor dictionaries for calculator rows."""

    visible_fields = visible_grid_fields(show_advanced)
    return [_row_to_table_data(row, visible_fields, currency_rates) for row in rows]


def table_data_to_rows(
    data: Iterable[Mapping[str, Any]],
    previous_rows: Iterable[CalculatorRow] = (),
) -> tuple[CalculatorRow, ...]:
    """Convert edited table dictionaries back into calculator rows."""

    previous_by_id = {row.row_id: row for row in previous_rows}
    rows: list[CalculatorRow] = []
    for index, item in enumerate(data, start=1):
        row_id = text_value(item.get("row_id")) or str(index)
        base_row = previous_by_id.get(row_id, CalculatorRow(row_id=row_id))
        values = {field.name: getattr(base_row, field.name) for field in fields(CalculatorRow)}
        for field_name, raw_value in item.items():
            if field_name in FORMULA_OVERRIDE_FIELD_BY_KEY.values():
                values[field_name] = formula_override_value(field_name, raw_value)
                continue
            if field_name in _ROW_FIELDS:
                values[field_name] = field_value(field_name, raw_value)
                continue
            override_field = FORMULA_OVERRIDE_FIELD_BY_KEY.get(str(field_name))
            if override_field:
                values[override_field] = formula_override_value(str(field_name), raw_value)
        if not values.get("row_id"):
            values["row_id"] = row_id
        values["supplier_currency"] = currency_or_default(values.get("supplier_currency"))
        values["sales_currency"] = currency_or_default(values.get("sales_currency"))
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


def _row_to_table_data(
    row: CalculatorRow,
    visible_fields: Iterable[str],
    currency_rates: Mapping[str, float] | None,
) -> dict[str, Any]:
    calculated = calculate_row(row, currency_rates)
    row_is_blank = row_has_no_user_values(row)
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
            data[field_name] = "" if row_is_blank else calculated.calculated_sales_price_per_unit
            continue
        if field_name == "sales_price_per_unit" and number_value(value) == 0 and number_value(row.gross_price_per_unit) > 0:
            data[field_name] = calculated.calculated_sales_price_per_unit
            continue
        if row_is_blank and field_name in NUMERIC_FIELDS:
            data[field_name] = None
            continue
        if field_name in PERCENT_UI_FIELDS:
            data[field_name] = decimal_to_percent(value)
            continue
        data[field_name] = value
    return data
