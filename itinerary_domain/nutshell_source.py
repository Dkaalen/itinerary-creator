"""Norway in a Nutshell source-row helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping

from itinerary_domain.nutshell_constants import NUTSHELL_CANONICAL_FAMILY, NUTSHELL_CONTRACT_KIND
from itinerary_domain.nutshell_parsing import _is_norway_in_a_nutshell_text


def _row_source(row: Mapping[str, Any] | None, extra_source: str = "") -> str:
    """Gather source fields in the order that preserves route/timetable evidence."""

    values: list[str] = []
    normalized_values: list[str] = []

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if not text:
            return
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        if any(normalized == existing or normalized in existing for existing in normalized_values):
            return
        values.append(text)
        normalized_values.append(normalized)

    if row:
        for key in (
            "details",
            "description_raw",
            "description",
            "route",
            "subtitle",
            "original_title",
            "title",
            "raw_text",
            "raw",
        ):
            add(row.get(key, ""))
        includes = row.get("source_includes") or row.get("supplier_includes") or row.get("includes") or ()
        if isinstance(includes, str):
            add(includes)
        else:
            for item in includes:
                add(item)
    if not values:
        add(extra_source)
    return "\n".join(values)


def _activity_product(row: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not row:
        return {}
    product = row.get("activity_product")
    return product if isinstance(product, Mapping) else {}


def is_nutshell_row(row: Mapping[str, Any] | None) -> bool:
    """Return True when the row is already classified or explicitly identifiable."""

    product = _activity_product(row)
    family = str(product.get("canonical_family", "") or "")
    if family:
        return family == NUTSHELL_CANONICAL_FAMILY
    contract = product.get("domain_contract")
    if isinstance(contract, Mapping):
        return contract.get("kind") == NUTSHELL_CONTRACT_KIND
    return _is_norway_in_a_nutshell_text(_row_source(row))


__all__ = ["_activity_product", "_row_source", "is_nutshell_row"]
