"""Suggest Local Library lines for typed Travel element grid cells."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from calculator.library_model import LocalLibraryRow
from calculator.library_search import LocalLibrarySearchResult, search_library_rows
from calculator.row_model import CalculatorRow

MIN_TRAVEL_ELEMENT_QUERY_LENGTH = 2
_FETCHED_SIGNAL_FIELDS = (
    "type",
    "supplier",
    "url",
    "comments",
    "gross_price_per_unit",
    "units",
    "sales_price_per_unit",
)


@dataclass(frozen=True)
class TravelElementSuggestionGroup:
    """Suggestions for one calculator row's Travel element query."""

    row_id: str
    query: str
    results: tuple[LocalLibrarySearchResult, ...]


def find_travel_element_suggestion_groups(
    rows: Iterable[CalculatorRow],
    library_rows: Iterable[LocalLibraryRow],
    *,
    limit_per_row: int = 8,
    max_rows: int = 1,
) -> tuple[TravelElementSuggestionGroup, ...]:
    """Return library suggestions for typed Travel element cells."""

    available_library_rows = tuple(library_rows)
    if not available_library_rows:
        return ()

    groups: list[TravelElementSuggestionGroup] = []
    for row in rows:
        query = row.travel_element.strip()
        if not _row_should_show_suggestions(row, query):
            continue
        results = search_library_rows(available_library_rows, query, limit=limit_per_row)
        if not results:
            continue
        groups.append(TravelElementSuggestionGroup(row_id=row.row_id, query=query, results=results))
        if len(groups) >= max_rows:
            break
    return tuple(groups)


def _row_should_show_suggestions(row: CalculatorRow, query: str) -> bool:
    if len(query) < MIN_TRAVEL_ELEMENT_QUERY_LENGTH:
        return False
    return not any(_has_value(getattr(row, field_name)) for field_name in _FETCHED_SIGNAL_FIELDS)


def _has_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) != 0.0
    return bool(str(value or "").strip())
