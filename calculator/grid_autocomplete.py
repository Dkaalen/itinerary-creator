"""Suggest Local Library lines for typed Travel element grid cells."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from calculator.library_model import LocalLibraryRow
from calculator.library_search import LocalLibrarySearchResult, search_library_rows
from calculator.row_model import CalculatorRow

MIN_TRAVEL_ELEMENT_QUERY_LENGTH = 2


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
    """Return library suggestions for typed Travel element cells.

    A calculator line may already contain day/date/type/price context when the
    user is trying to fetch a library line. Those context fields must not block
    suggestions; the selected fetch action will preserve the useful context and
    replace the line details.
    """

    available_library_rows = tuple(library_rows)
    if not available_library_rows:
        return ()

    groups: list[TravelElementSuggestionGroup] = []
    for row in rows:
        query = row.travel_element.strip()
        if len(query) < MIN_TRAVEL_ELEMENT_QUERY_LENGTH:
            continue
        results = search_library_rows(available_library_rows, query, limit=limit_per_row)
        if not results:
            continue
        groups.append(TravelElementSuggestionGroup(row_id=row.row_id, query=query, results=results))
        if len(groups) >= max_rows:
            break
    return tuple(groups)
