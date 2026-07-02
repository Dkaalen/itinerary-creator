"""Normalize source rows into Local Library rows."""

from __future__ import annotations

import hashlib
import re
from dataclasses import fields
from typing import Mapping

from calculator.library_model import (
    FORMULA_FIELD_NAMES,
    LINE_RECORD_TYPE,
    LOCAL_LIBRARY_FIELD_BY_HEADER,
    LOCAL_LIBRARY_SCHEMA_VERSION,
    LocalLibraryRow,
)
from calculator.row_model import CalculatorRow

_FIELD_NAMES = {field.name for field in fields(LocalLibraryRow)}
_BOOL_FIELDS = {"is_deleted", "is_fetchable", "manual_booking", "non_refundable", "refundable"}
_FLOAT_FIELDS = {
    "gross_price_per_unit",
    "units",
    "gross_price",
    "supplier_commission",
    "net_price",
    "supplier_x_rate",
    "net_price_nok",
    "sales_price_per_unit",
    "price",
    "sales_x_rate",
    "sales_price_nok_total",
    "gp_nok",
    "gp_percent",
    "vat25",
    "vat15",
    "vat12",
    "vat0_domestic",
    "vat0_international",
}
_TEXT_FIELDS = _FIELD_NAMES - _BOOL_FIELDS - _FLOAT_FIELDS - {"source_row"}
_EXTERNAL_CURR_REFERENCE_RE = re.compile(r"'?\[[^\]]+\]Curr'?!")
_SPACE_RE = re.compile(r"\s+")


def normalize_library_mapping(raw_row: Mapping[str, object]) -> LocalLibraryRow:
    """Return one normalized Local Library row from sheet headers or field names."""

    normalized = _blank_values()
    for key, value in raw_row.items():
        field_name = _field_name(str(key))
        if field_name in normalized:
            normalized[field_name] = _normalize_value(field_name, value)

    normalized["schema_version"] = normalized["schema_version"] or LOCAL_LIBRARY_SCHEMA_VERSION
    normalized["record_type"] = (normalized["record_type"] or LINE_RECORD_TYPE).lower()
    normalized["supplier_currency"] = _currency(normalized["supplier_currency"])
    normalized["sales_currency"] = _currency(normalized["sales_currency"])
    normalized["category"] = normalized["category"] or normalized["type"]
    normalized["library_id"] = normalized["library_id"] or _stable_library_id(normalized)
    normalized["search_text"] = normalized["search_text"] or build_search_text(normalized)
    return LocalLibraryRow(**normalized)


def normalize_library_rows(raw_rows: object) -> tuple[LocalLibraryRow, ...]:
    """Normalize many raw rows while dropping completely empty rows."""

    rows = []
    for raw_row in raw_rows:  # type: ignore[operator]
        if not isinstance(raw_row, Mapping) or _is_empty(raw_row):
            continue
        rows.append(normalize_library_mapping(raw_row))
    return tuple(rows)


def library_row_to_calculator_row(row: LocalLibraryRow, row_id: str = "") -> CalculatorRow:
    """Convert one library row into a calculator row without storage metadata."""

    return CalculatorRow(
        row_id=row_id,
        day=row.day,
        type=row.type,
        from_date=row.from_date,
        to_date=row.to_date,
        from_time=row.from_time,
        to_time=row.to_time,
        supplier=row.supplier,
        travel_element=row.travel_element,
        manual_booking=row.manual_booking,
        status=row.status,
        comments=row.comments,
        non_refundable=row.non_refundable,
        refundable=row.refundable,
        url=row.url,
        gross_price_per_unit=row.gross_price_per_unit,
        units=row.units,
        supplier_commission=row.supplier_commission,
        supplier_currency=row.supplier_currency,
        sales_price_per_unit=row.sales_price_per_unit,
        sales_currency=row.sales_currency,
        vat25=row.vat25,
        vat15=row.vat15,
        vat12=row.vat12,
        vat0_domestic=row.vat0_domestic,
        vat0_international=row.vat0_international,
    )


def clean_formula_text(value: object) -> str:
    """Return stored formula text without old external workbook references."""

    text = _text(value)
    if text.startswith("'"):
        text = text[1:]
    return _EXTERNAL_CURR_REFERENCE_RE.sub("Curr!", text)


def build_search_text(values: Mapping[str, object]) -> str:
    """Build normalized search text from the user-facing library fields."""

    parts = [
        values.get("country"),
        values.get("category"),
        values.get("type"),
        values.get("supplier"),
        values.get("travel_element"),
        values.get("comments"),
        values.get("url"),
    ]
    return _SPACE_RE.sub(" ", " | ".join(_text(part) for part in parts if _text(part))).strip()


def _blank_values() -> dict[str, object]:
    row = LocalLibraryRow()
    return {field.name: getattr(row, field.name) for field in fields(LocalLibraryRow)}


def _field_name(key: str) -> str:
    stripped = key.strip()
    return LOCAL_LIBRARY_FIELD_BY_HEADER.get(stripped, stripped)


def _normalize_value(field_name: str, value: object) -> object:
    if field_name in FORMULA_FIELD_NAMES:
        return clean_formula_text(value)
    if field_name in _BOOL_FIELDS:
        return _bool(value)
    if field_name in _FLOAT_FIELDS:
        return _optional_float(value) if field_name == "sales_price_per_unit" else _float(value)
    if field_name == "source_row":
        return _int_or_none(value)
    if field_name in _TEXT_FIELDS:
        return _text(value)
    return value


def _stable_library_id(values: Mapping[str, object]) -> str:
    seed = "|".join(
        _text(values.get(key))
        for key in ("source_sheet", "source_row", "country", "category", "type", "travel_element")
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    prefix = _text(values.get("country") or values.get("source_sheet") or "lib").lower()
    prefix = re.sub(r"[^a-z0-9]+", "_", prefix).strip("_") or "lib"
    return f"{prefix}_{digest}"


def _is_empty(raw_row: Mapping[str, object]) -> bool:
    return not any(_text(value) for value in raw_row.values())


def _currency(value: object) -> str:
    return (_text(value) or "NOK").upper()


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = _text(value).lower()
    return text in {"1", "true", "yes", "y", "x"}


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return _float(value)


def _float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value).replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
