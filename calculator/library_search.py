"""Search Local Library rows for calculator fetch results."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Iterable

from calculator.library_model import LocalLibraryRow

_DEFAULT_LIMIT = 25
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SPECIAL_CHARACTER_TRANSLATION = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "å": "a", "Å": "A"})
_FIELD_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("travel_element", 50),
    ("supplier", 35),
    ("country", 25),
    ("category", 25),
    ("type", 25),
    ("comments", 15),
    ("search_text", 10),
    ("url", 5),
)


@dataclass(frozen=True)
class LocalLibrarySearchResult:
    """One ranked Local Library search result."""

    row: LocalLibraryRow
    score: int
    matched_fields: tuple[str, ...]


def search_library_rows(
    rows: Iterable[LocalLibraryRow],
    query: str,
    *,
    limit: int = _DEFAULT_LIMIT,
) -> tuple[LocalLibrarySearchResult, ...]:
    """Return ranked active/fetchable Local Library rows for a query."""

    fetchable_rows = tuple(row for row in rows if row.is_available_for_fetch)
    normalized_query = _normalize(query)
    query_tokens = _tokens(normalized_query)
    if not query_tokens:
        return tuple(_blank_query_result(row) for row in _sort_rows(fetchable_rows)[:limit])

    results = [_score_row(row, normalized_query, query_tokens) for row in fetchable_rows]
    matches = [result for result in results if result.score > 0]
    matches.sort(key=lambda result: (-result.score, _sort_key(result.row)))
    return tuple(matches[:limit])


def library_result_label(row: LocalLibraryRow) -> str:
    """Return a compact UI label for one Local Library row."""

    prefix = " · ".join(part for part in (row.country, row.category or row.type, row.supplier) if part)
    title = row.travel_element or row.comments or row.url or row.library_id
    return f"{prefix} — {title}" if prefix else title


def library_result_preview(row: LocalLibraryRow) -> str:
    """Return human-readable preview text for one Local Library row."""

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
    return "\n".join(part for part in parts if part)


def _blank_query_result(row: LocalLibraryRow) -> LocalLibrarySearchResult:
    return LocalLibrarySearchResult(row=row, score=0, matched_fields=())


def _score_row(
    row: LocalLibraryRow,
    normalized_query: str,
    query_tokens: tuple[str, ...],
) -> LocalLibrarySearchResult:
    score = 0
    matched_fields: list[str] = []
    for field_name, weight in _FIELD_WEIGHTS:
        field_value = _normalize(getattr(row, field_name, ""))
        if not field_value:
            continue
        field_tokens = set(_tokens(field_value))
        token_matches = sum(1 for token in query_tokens if token in field_tokens or token in field_value)
        if token_matches == 0 and normalized_query not in field_value:
            continue
        matched_fields.append(field_name)
        score += token_matches * weight
        if normalized_query and normalized_query in field_value:
            score += weight * 2
    return LocalLibrarySearchResult(row=row, score=score, matched_fields=tuple(matched_fields))


def _sort_rows(rows: Iterable[LocalLibraryRow]) -> list[LocalLibraryRow]:
    return sorted(rows, key=_sort_key)


def _sort_key(row: LocalLibraryRow) -> tuple[str, str, str, str]:
    return (
        _normalize(row.country),
        _normalize(row.category or row.type),
        _normalize(row.supplier),
        _normalize(row.travel_element or row.comments or row.library_id),
    )


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(value))


def _normalize(value: object) -> str:
    text = str(value or "").translate(_SPECIAL_CHARACTER_TRANSLATION)
    text = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(ascii_text.lower().split())
