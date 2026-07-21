"""Canonical Local Library normalization, ranking, routing, and alias rules."""

from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Mapping, Sequence

from calculator.library_model import LocalLibraryRow

LOCAL_LIBRARY_RANKING_VERSION = "local-library-ranking-v1"

# This JSON-compatible mapping is the only maintained rule data for Local
# Library autocomplete ranking. Python consumes it directly and the browser
# receives an exact copy through the Calculator component payload.
LOCAL_LIBRARY_RANKING_SPEC: dict[str, object] = {
    "version": LOCAL_LIBRARY_RANKING_VERSION,
    "minimum_query_length": 2,
    "normalization": {
        "unicode_form": "NFKD",
        "transliteration": {"ø": "o", "æ": "ae", "å": "a"},
    },
    "search_fields": [
        {"name": "travel_element", "weight": 70},
        {"name": "supplier", "weight": 42},
        {"name": "country", "weight": 25},
        {"name": "category", "weight": 28},
        {"name": "source_sheet", "weight": 34},
        {"name": "type", "weight": 34},
        {"name": "comments", "weight": 12},
        {"name": "search_text", "weight": 10},
        {"name": "url", "weight": 3},
        {"name": "label", "weight": 12},
        {"name": "preview", "weight": 8},
    ],
    "match_weights": {
        "query_exact": 16,
        "query_prefix": 10,
        "query_contains": 6,
        "token_exact": 6,
        "token_prefix": 4,
        "token_contains": 2,
    },
    "context_weights": {
        "sheet_exact": 1400,
        "sheet_alias": 1100,
        "sheet_mismatch": -220,
        "type_exact": 900,
        "type_alias": 700,
        "type_partial": 450,
        "type_mismatch": -160,
        "country_in_context": 300,
        "supplier_exact": 360,
        "supplier_in_context": 180,
    },
    "sheet_routes": [
        {"sheet": "hotels", "terms": ["hotel", "accommodation", "overnight"]},
        {"sheet": "transfers", "terms": ["transfer", "airport", "station", "pickup", "drop off"]},
        {"sheet": "transport", "terms": ["coach", "train", "rail", "flight", "ferry", "boat", "transport"]},
        {"sheet": "activities", "terms": ["activity", "tour", "museum", "excursion", "visit", "experience"]},
        {"sheet": "general", "terms": ["arrival", "departure", "leisure", "welcome"]},
    ],
    "cross_type_aliases": [
        {
            "id": "norway_in_a_nutshell",
            "phrase": "norway in a nutshell",
            "context_types": ["activity", "transfer"],
            "context_sheets": ["activities", "transfers"],
            "source_types": ["activity", "transfer", "transport"],
            "source_sheets": ["activities", "transfers", "transport"],
        }
    ],
    "tie_break": ["source_sheet", "source_row", "label", "library_id"],
}

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_SPACE_RE = re.compile(r"\s+")


def local_library_ranking_spec_payload() -> dict[str, object]:
    """Return an isolated JSON-compatible copy of the canonical rule data."""

    return deepcopy(LOCAL_LIBRARY_RANKING_SPEC)


def normalize_search_text(value: object) -> str:
    """Normalize Nordic text and punctuation according to the shared spec."""

    normalization = _mapping(LOCAL_LIBRARY_RANKING_SPEC.get("normalization"))
    text = str(value or "").lower()
    for source, replacement in _mapping(normalization.get("transliteration")).items():
        text = text.replace(str(source), str(replacement))
    unicode_form = str(normalization.get("unicode_form") or "NFKD")
    text = unicodedata.normalize(unicode_form, text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    return _SPACE_RE.sub(" ", _NON_ALNUM_RE.sub(" ", text)).strip()


def search_tokens(value: object) -> tuple[str, ...]:
    """Return canonical normalized tokens."""

    normalized = normalize_search_text(value)
    return tuple(normalized.split()) if normalized else ()


def expected_library_sheet(row_type: object, travel_element: object) -> str:
    """Resolve the first matching worksheet route from the canonical rules."""

    context_text = normalize_search_text(f"{row_type or ''} {travel_element or ''}")
    for route in _sequence(LOCAL_LIBRARY_RANKING_SPEC.get("sheet_routes")):
        route_mapping = _mapping(route)
        for term in _sequence(route_mapping.get("terms")):
            normalized_term = normalize_search_text(term)
            if normalized_term and normalized_term in context_text:
                return normalize_search_text(route_mapping.get("sheet"))
    return ""


def library_search_field_value(row: LocalLibraryRow, field_name: str) -> object:
    """Return one canonical searchable value, including computed UI fields."""

    if field_name == "label":
        return library_result_label(row)
    if field_name == "preview":
        return library_result_preview(row)
    return getattr(row, field_name, "")


def library_result_label(row: LocalLibraryRow) -> str:
    """Return the shared compact label used in ranking and browser display."""

    prefix = " · ".join(part for part in (row.country, row.category or row.type, row.supplier) if part)
    title = row.travel_element or row.comments or row.url or row.library_id
    return f"{prefix} — {title}" if prefix else title


def library_result_preview(row: LocalLibraryRow) -> str:
    """Return the shared informative preview used in ranking and display."""

    parts = [
        row.travel_element,
        f"Supplier: {row.supplier}" if row.supplier else "",
        f"Type: {row.type}" if row.type else "",
        f"Country: {row.country}" if row.country else "",
        f"Price/unit: {row.gross_price_per_unit:g} {row.supplier_currency}" if row.gross_price_per_unit else "",
        f"Sales/unit: {row.sales_price_per_unit:g} {row.sales_currency}" if row.sales_price_per_unit else "",
        row.comments,
        row.url,
    ]
    return " • ".join(part for part in parts if part)[:450]


def matching_cross_type_alias(
    row: LocalLibraryRow,
    normalized_query: str,
    *,
    row_type: object,
    expected_sheet: object,
) -> Mapping[str, object] | None:
    """Return the first query-gated compatibility alias matching one row."""

    normalized_type = normalize_search_text(row_type)
    normalized_expected_sheet = normalize_search_text(expected_sheet)
    item_text = normalize_search_text(
        " ".join(
            str(library_search_field_value(row, str(field.get("name") or "")) or "")
            for field in map(_mapping, _sequence(LOCAL_LIBRARY_RANKING_SPEC.get("search_fields")))
        )
    )
    source_type = normalize_search_text(row.type or row.category)
    source_sheet = normalize_search_text(row.source_sheet or row.category)

    for alias in map(_mapping, _sequence(LOCAL_LIBRARY_RANKING_SPEC.get("cross_type_aliases"))):
        phrase = normalize_search_text(alias.get("phrase"))
        if not phrase or phrase not in normalized_query or phrase not in item_text:
            continue
        context_types = _normalized_values(alias.get("context_types"))
        context_sheets = _normalized_values(alias.get("context_sheets"))
        source_types = _normalized_values(alias.get("source_types"))
        source_sheets = _normalized_values(alias.get("source_sheets"))
        if normalized_type not in context_types:
            continue
        if normalized_expected_sheet and normalized_expected_sheet not in context_sheets:
            continue
        if source_type not in source_types or source_sheet not in source_sheets:
            continue
        return alias
    return None


def local_library_sort_key(row: LocalLibraryRow) -> tuple[str, int, str, str]:
    """Return the canonical deterministic tie-break, preserving duplicates."""

    return (
        normalize_search_text(row.source_sheet),
        int(row.source_row) if row.source_row is not None else 2_147_483_647,
        normalize_search_text(library_result_label(row)),
        str(row.library_id or ""),
    )


def _normalized_values(value: object) -> set[str]:
    return {normalize_search_text(item) for item in _sequence(value) if normalize_search_text(item)}


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else ()


__all__ = [
    "LOCAL_LIBRARY_RANKING_SPEC",
    "LOCAL_LIBRARY_RANKING_VERSION",
    "expected_library_sheet",
    "library_result_label",
    "library_result_preview",
    "library_search_field_value",
    "local_library_ranking_spec_payload",
    "local_library_sort_key",
    "matching_cross_type_alias",
    "normalize_search_text",
    "search_tokens",
]
