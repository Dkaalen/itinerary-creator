"""Scalar value normalization for calculator grid rows."""

from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime
import re
from typing import Any

from calculator.defaults import DEFAULT_CALCULATOR_CURRENCY
from calculator.numeric_input import optional_numeric_input, parse_decimal_input_strict, parse_numeric_input
from calculator.row_model import FORMULA_OVERRIDE_FIELDS, CalculatorRow

NUMERIC_FIELDS = {
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
BOOLEAN_FIELDS = {"manual_booking", "non_refundable", "refundable"}
OPTIONAL_NUMERIC_FIELDS = {"sales_price_per_unit"}
BLANK_NUMERIC_MARKERS = {"", "none", "nan", "null"}
DEFAULT_ONLY_TEXT_FIELDS = {"row_id", "supplier_currency", "sales_currency"}
PERCENT_UI_FIELDS = {"supplier_commission"}


def field_value(field_name: str, value: Any) -> Any:
    """Normalize a table-cell value for a dataclass field."""

    if field_name in BOOLEAN_FIELDS:
        return bool_value(value)
    if field_name in OPTIONAL_NUMERIC_FIELDS:
        return editable_number_value(value, optional=True)
    if field_name in PERCENT_UI_FIELDS:
        return percent_to_decimal(value)
    if field_name in NUMERIC_FIELDS:
        return editable_number_value(value)
    return text_value(value)


def formula_override_value(field_name: str, value: Any) -> float | str | None:
    """Normalize a formula override cell value."""

    if value is None:
        return None
    text = str(value).strip()
    if text.casefold() in BLANK_NUMERIC_MARKERS:
        return None
    if field_name in {"gp_percent", "gp_percent_override"}:
        return percent_to_decimal(text)
    return editable_number_value(text, optional=True)


def text_value(value: Any) -> str:
    """Return normalized text suitable for calculator row fields."""

    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text = str(value).strip()
    return "" if text.casefold() in BLANK_NUMERIC_MARKERS else text


def number_value(value: Any) -> float:
    return parse_numeric_input(value)


def optional_number_value(value: Any) -> float | None:
    return optional_numeric_input(value)


def editable_number_value(value: Any, *, optional: bool = False) -> float | str | None:
    """Preserve unfinished formulas instead of silently replacing them with zero."""

    if value is None:
        return None if optional else 0.0
    text = str(value).strip()
    if text.casefold() in BLANK_NUMERIC_MARKERS:
        return None if optional else 0.0
    try:
        parsed = parse_decimal_input_strict(value, allow_blank=optional)
    except ValueError:
        return text
    if parsed is None:
        return None if optional else 0.0
    return float(parsed)


def percent_to_decimal(value: Any) -> float | str:
    """Convert UI percentage input to the decimal value used by formulas."""

    if value is None:
        return 0.0
    text = str(value).strip()
    try:
        parsed = parse_decimal_input_strict(value)
    except ValueError:
        if not text.startswith("="):
            return text
        expression = text[1:].strip()
        return f"=({expression})/100"
    number = 0.0 if parsed is None else float(parsed)
    if number == 0:
        return 0.0
    return number if "%" in text else number / 100


def decimal_to_percent(value: Any) -> float | str:
    """Convert formula decimal percentage to the visible grid percentage."""

    if isinstance(value, str):
        text = value.strip()
        wrapped = re.fullmatch(r"=\((.*)\)/100", text, flags=re.DOTALL)
        if wrapped:
            return f"={wrapped.group(1)}"
        try:
            parsed = parse_decimal_input_strict(text)
        except ValueError:
            if not text.startswith("="):
                return text
            expression = text[1:].strip()
            return f"=({expression})*100"
        return (0.0 if parsed is None else float(parsed)) * 100
    return number_value(value) * 100


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "checked"}


def currency_or_default(value: object) -> str:
    text = text_value(value).upper()
    return text or DEFAULT_CALCULATOR_CURRENCY


def row_has_no_user_values(row: CalculatorRow) -> bool:
    """Return whether the row only contains generated/default calculator values."""

    for field in fields(CalculatorRow):
        field_name = field.name
        if field_name in DEFAULT_ONLY_TEXT_FIELDS:
            continue
        value = getattr(row, field_name)
        if value_has_content(value):
            return False
    return True


def value_has_content(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) != 0.0
    return bool(str(value or "").strip())


__all__ = [
    "BLANK_NUMERIC_MARKERS",
    "BOOLEAN_FIELDS",
    "DEFAULT_ONLY_TEXT_FIELDS",
    "NUMERIC_FIELDS",
    "OPTIONAL_NUMERIC_FIELDS",
    "PERCENT_UI_FIELDS",
    "bool_value",
    "currency_or_default",
    "decimal_to_percent",
    "editable_number_value",
    "field_value",
    "formula_override_value",
    "number_value",
    "optional_number_value",
    "percent_to_decimal",
    "row_has_no_user_values",
    "text_value",
    "value_has_content",
]
