"""Pure helpers for editing Local Library rows in the app."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Mapping
from uuid import uuid4

from calculator.defaults import DEFAULT_CALCULATOR_CURRENCY
from calculator.library_model import LINE_RECORD_TYPE, LocalLibraryRow

LOCAL_LIBRARY_EDITOR_SOURCE = "app_local_library_manager"
LOCAL_LIBRARY_EDITOR_USER = "streamlit_app"
_PERCENT_FIELDS = {"supplier_commission", "gp_percent"}
_BOOL_FIELDS = {"is_fetchable", "manual_booking", "non_refundable", "refundable"}
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
_TEXT_FIELDS = {
    "country",
    "category",
    "kalk_id",
    "day",
    "type",
    "from_date",
    "to_date",
    "from_time",
    "to_time",
    "supplier",
    "travel_element",
    "status",
    "comments",
    "url",
    "supplier_currency",
    "sales_currency",
    "search_text",
}
EDITABLE_LIBRARY_FIELDS = tuple(sorted(_BOOL_FIELDS | _FLOAT_FIELDS | _TEXT_FIELDS))


def new_local_library_row(*, now: datetime | None = None, library_id: str | None = None) -> LocalLibraryRow:
    """Return a new active Local Library line row ready for manual editing."""

    timestamp = _timestamp(now)
    return LocalLibraryRow(
        library_id=library_id or f"manual_{uuid4().hex[:12]}",
        is_deleted=False,
        is_fetchable=True,
        record_type=LINE_RECORD_TYPE,
        source_workbook=LOCAL_LIBRARY_EDITOR_SOURCE,
        source_sheet="Local Library Manager",
        supplier_currency=DEFAULT_CALCULATOR_CURRENCY,
        sales_currency=DEFAULT_CALCULATOR_CURRENCY,
        created_at=timestamp,
        updated_at=timestamp,
        updated_by=LOCAL_LIBRARY_EDITOR_USER,
    )


def update_local_library_row(
    row: LocalLibraryRow,
    values: Mapping[str, object],
    *,
    now: datetime | None = None,
) -> LocalLibraryRow:
    """Return ``row`` with validated editor values and refreshed metadata."""

    changes: dict[str, object] = {
        "updated_at": _timestamp(now),
        "updated_by": LOCAL_LIBRARY_EDITOR_USER,
        "record_type": LINE_RECORD_TYPE,
        "is_deleted": False,
    }
    for field_name in EDITABLE_LIBRARY_FIELDS:
        if field_name not in values:
            continue
        changes[field_name] = _field_value(field_name, values[field_name])
    changes["supplier_currency"] = _currency(changes.get("supplier_currency", row.supplier_currency))
    changes["sales_currency"] = _currency(changes.get("sales_currency", row.sales_currency))
    changes["search_text"] = str(changes.get("search_text") or "").strip()
    return replace(row, **changes)


def mark_local_library_row_deleted(row: LocalLibraryRow, *, now: datetime | None = None) -> LocalLibraryRow:
    """Return a soft-deleted row so Google Sheets history remains recoverable."""

    return replace(
        row,
        is_deleted=True,
        is_fetchable=False,
        updated_at=_timestamp(now),
        updated_by=LOCAL_LIBRARY_EDITOR_USER,
    )


def display_label_for_local_library_row(row: LocalLibraryRow) -> str:
    """Return a compact selectbox label for one Local Library row."""

    element = row.travel_element or row.supplier or row.library_id or "Untitled row"
    prefix = " · ".join(part for part in (row.country, row.category or row.type) if part)
    suffix = " deleted" if row.is_deleted else ""
    return f"{prefix} · {element}{suffix}" if prefix else f"{element}{suffix}"


def _field_value(field_name: str, value: object) -> object:
    if field_name in _BOOL_FIELDS:
        return _bool(value)
    if field_name in _PERCENT_FIELDS:
        return _percent_to_decimal(value)
    if field_name in _FLOAT_FIELDS:
        return _float(value)
    if field_name in {"supplier_currency", "sales_currency"}:
        return _currency(value)
    return str(value or "").strip()


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "checked", "x"}


def _float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "").replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _percent_to_decimal(value: object) -> float:
    number = _float(value)
    return 0.0 if number == 0 else number / 100


def _currency(value: object) -> str:
    return str(value or DEFAULT_CALCULATOR_CURRENCY).strip().upper() or DEFAULT_CALCULATOR_CURRENCY


def _timestamp(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
