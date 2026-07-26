"""Build payloads for the browser-side calculator grid component."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from threading import RLock
from typing import Any, Mapping

from app_modules.calculator_grid_data import rows_to_table_data
from app_modules.calculator_grid_values import decimal_to_percent
from app_modules.calculator_library_transport import calculator_library_rows_are_acknowledged
from calculator.calculator_state import CalculatorState
from calculator.currency_rates import normalize_currency_rates
from calculator.financial_rules import financial_rules_payload
from calculator.library_model import LocalLibraryRow
from calculator.library_ranking import (
    LOCAL_LIBRARY_RANKING_VERSION,
    local_library_ranking_spec_payload,
)
from calculator.library_read_summary import summarize_local_library_read
from calculator.library_store import LocalLibraryReadResult
from calculator.state_revision import calculator_state_revision

_LIBRARY_PAYLOAD_VERSION = "compact-v2"
_LIBRARY_ROW_FIELDS: tuple[str, ...] = (
    "day",
    "type",
    "from_date",
    "to_date",
    "from_time",
    "to_time",
    "supplier",
    "travel_element",
    "manual_booking",
    "status",
    "comments",
    "non_refundable",
    "refundable",
    "url",
    "gross_price_per_unit",
    "units",
    "supplier_commission",
    "supplier_currency",
    "sales_price_per_unit",
    "sales_currency",
    "vat25",
    "vat15",
    "vat12",
    "vat0_domestic",
    "vat0_international",
)
_LIBRARY_PAYLOAD_CACHE: dict[str, tuple[dict[str, Any], ...]] = {}
_LIBRARY_PAYLOAD_CACHE_LOCK = RLock()
_LIBRARY_PAYLOAD_CACHE_LIMIT = 6


def build_calculator_grid_payload(
    state: CalculatorState,
    library_read: LocalLibraryReadResult,
    *,
    show_advanced: bool = False,
    currency_rates: Mapping[str, float] | None = None,
    draft_namespace: str = "",
    project_identity: str = "",
    pending_download: Mapping[str, Any] | None = None,
    component_ack: Mapping[str, Any] | None = None,
    browser_library_ack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the JSON-serializable component payload for the calculator grid."""

    active_rates = normalize_currency_rates(currency_rates)
    library_fingerprint = _library_fingerprint(library_read)
    library_rows = _cached_library_rows(library_read, library_fingerprint)
    library_row_count = len(library_rows)
    rows_acknowledged = calculator_library_rows_are_acknowledged(
        browser_library_ack,
        fingerprint=library_fingerprint,
        payload_version=_LIBRARY_PAYLOAD_VERSION,
        row_count=library_row_count,
    )
    return {
        "itinerary_name": state.itinerary_name,
        "number_of_pax": state.number_of_pax,
        "rows": rows_to_table_data(state.rows, show_advanced=True, currency_rates=active_rates),
        "state_revision": calculator_state_revision(state),
        "draft_storage_key": _draft_storage_key(draft_namespace),
        "project_identity": str(project_identity or draft_namespace or ""),
        "show_advanced": show_advanced,
        "currency_rates": active_rates,
        "financial_rules": financial_rules_payload(),
        "library_status": _library_read_status(library_read),
        "library_source": library_read.source,
        "library_read_only": library_read.read_only,
        "library_message": library_read.message,
        "library_payload_version": _LIBRARY_PAYLOAD_VERSION,
        "library_fingerprint": library_fingerprint,
        "library_row_fields": _LIBRARY_ROW_FIELDS,
        "library_ranking_spec": local_library_ranking_spec_payload(),
        "library_row_count": library_row_count,
        "library_rows": () if rows_acknowledged else library_rows,
        "pending_download": dict(pending_download or {}),
        "component_ack": dict(component_ack or {}),
    }



def clear_calculator_library_payload_cache() -> None:
    """Forget prepared browser library payloads."""

    with _LIBRARY_PAYLOAD_CACHE_LOCK:
        _LIBRARY_PAYLOAD_CACHE.clear()


def _cached_library_rows(
    read_result: LocalLibraryReadResult,
    fingerprint: str,
) -> tuple[dict[str, Any], ...]:
    with _LIBRARY_PAYLOAD_CACHE_LOCK:
        cached = _LIBRARY_PAYLOAD_CACHE.get(fingerprint)
        if cached is not None:
            return cached

    prepared = tuple(_compact_library_row_payload(row) for row in _autocomplete_rows(read_result))
    with _LIBRARY_PAYLOAD_CACHE_LOCK:
        if len(_LIBRARY_PAYLOAD_CACHE) >= _LIBRARY_PAYLOAD_CACHE_LIMIT:
            oldest_key = next(iter(_LIBRARY_PAYLOAD_CACHE))
            _LIBRARY_PAYLOAD_CACHE.pop(oldest_key, None)
        _LIBRARY_PAYLOAD_CACHE[fingerprint] = prepared
    return prepared


def _compact_library_row_payload(row: LocalLibraryRow) -> dict[str, Any]:
    values = {
        str(index): value
        for index, field_name in enumerate(_LIBRARY_ROW_FIELDS)
        if _library_payload_value_is_meaningful(
            value := _library_field_value(row, field_name)
        )
    }
    return {
        "i": row.library_id,
        "w": row.source_sheet,
        "x": row.source_row,
        "c": row.country,
        "g": row.category,
        "v": values,
    }


def _library_field_value(row: LocalLibraryRow, field_name: str) -> Any:
    value = getattr(row, field_name)
    if field_name == "supplier_commission":
        return decimal_to_percent(value)
    return value


def _library_payload_value_is_meaningful(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)):
        return float(value) != 0.0
    return bool(str(value).strip())


def _library_fingerprint(read_result: LocalLibraryReadResult) -> str:
    explicit = str(read_result.fingerprint or "").strip()
    if explicit:
        return f"{_LIBRARY_PAYLOAD_VERSION}:{LOCAL_LIBRARY_RANKING_VERSION}:{explicit}"
    identity = json.dumps(
        [asdict(row) for row in _autocomplete_rows(read_result)],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"{_LIBRARY_PAYLOAD_VERSION}:{LOCAL_LIBRARY_RANKING_VERSION}:inline:{digest}"


def _library_read_status(read_result: LocalLibraryReadResult) -> str:
    return summarize_local_library_read(read_result).component_text



def _autocomplete_rows(read_result: LocalLibraryReadResult) -> tuple[LocalLibraryRow, ...]:
    """Return rows available to the browser autocomplete."""

    return tuple(row for row in read_result.rows if row.is_available_for_fetch)


def _draft_storage_key(namespace: str) -> str:
    """Return a project-scoped browser draft key for the calculator grid."""

    safe = re.sub(r"[^A-Za-z0-9_.:-]+", "_", str(namespace or "global")).strip("_")
    return f"itineraryCalculatorBrowserDraft.v3.{safe or 'global'}"


__all__ = [
    "build_calculator_grid_payload",
    "calculator_state_revision",
    "clear_calculator_library_payload_cache",
]
