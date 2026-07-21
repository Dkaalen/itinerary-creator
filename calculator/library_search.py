"""Python reference search using the canonical Local Library ranking spec."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from calculator.library_model import LocalLibraryRow
from calculator.library_ranking import (
    LOCAL_LIBRARY_RANKING_SPEC,
    expected_library_sheet,
    library_result_label,
    library_result_preview,
    library_search_field_value,
    local_library_sort_key,
    matching_cross_type_alias,
    normalize_search_text,
    search_tokens,
)

_DEFAULT_LIMIT = 25


@dataclass(frozen=True)
class LocalLibrarySearchContext:
    """Calculator-row context used for deterministic relevance bonuses."""

    type: str = ""
    travel_element: str = ""
    supplier: str = ""
    comments: str = ""


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
    context: LocalLibrarySearchContext | Mapping[str, object] | None = None,
) -> tuple[LocalLibrarySearchResult, ...]:
    """Return ranked active/fetchable rows using the browser-shared rules."""

    fetchable_rows = tuple(row for row in rows if row.is_available_for_fetch)
    normalized_query = normalize_search_text(query)
    query_tokens = search_tokens(normalized_query)
    if not query_tokens:
        return tuple(_blank_query_result(row) for row in sorted(fetchable_rows, key=local_library_sort_key)[:limit])

    active_context = _coerce_context(context, query)
    results = [_score_row(row, normalized_query, query_tokens, active_context) for row in fetchable_rows]
    matches = [result for result in results if result.score > 0]
    matches.sort(key=lambda result: (-result.score, local_library_sort_key(result.row)))
    return tuple(matches[: max(0, int(limit))])


def _coerce_context(
    context: LocalLibrarySearchContext | Mapping[str, object] | None,
    query: str,
) -> LocalLibrarySearchContext:
    if isinstance(context, LocalLibrarySearchContext):
        return context
    if isinstance(context, Mapping):
        return LocalLibrarySearchContext(
            type=str(context.get("type") or ""),
            travel_element=str(context.get("travel_element") or query),
            supplier=str(context.get("supplier") or ""),
            comments=str(context.get("comments") or ""),
        )
    return LocalLibrarySearchContext(travel_element=query)


def _blank_query_result(row: LocalLibraryRow) -> LocalLibrarySearchResult:
    return LocalLibrarySearchResult(row=row, score=0, matched_fields=())


def _score_row(
    row: LocalLibraryRow,
    normalized_query: str,
    query_tokens: tuple[str, ...],
    context: LocalLibrarySearchContext,
) -> LocalLibrarySearchResult:
    match_weights = _int_mapping(LOCAL_LIBRARY_RANKING_SPEC.get("match_weights"))
    score = 0
    matched_fields: list[str] = []
    for field_rule in _mapping_sequence(LOCAL_LIBRARY_RANKING_SPEC.get("search_fields")):
        field_name = str(field_rule.get("name") or "")
        field_weight = int(field_rule.get("weight") or 0)
        field_value = normalize_search_text(library_search_field_value(row, field_name))
        field_score = _field_match_score(field_value, normalized_query, query_tokens, match_weights)
        if field_score <= 0:
            continue
        matched_fields.append(field_name)
        score += field_score * field_weight
    score += _context_score(row, normalized_query, context)
    return LocalLibrarySearchResult(row=row, score=score, matched_fields=tuple(matched_fields))


def _field_match_score(
    field_value: str,
    normalized_query: str,
    query_tokens: tuple[str, ...],
    weights: Mapping[str, int],
) -> int:
    if not field_value:
        return 0
    field_tokens = tuple(field_value.split())
    score = 0
    if field_value == normalized_query:
        score += weights.get("query_exact", 0)
    elif field_value.startswith(normalized_query):
        score += weights.get("query_prefix", 0)
    elif normalized_query in field_value:
        score += weights.get("query_contains", 0)

    for token in query_tokens:
        if token in field_tokens:
            score += weights.get("token_exact", 0)
        elif any(field_token.startswith(token) for field_token in field_tokens):
            score += weights.get("token_prefix", 0)
        elif token in field_value:
            score += weights.get("token_contains", 0)
    return score


def _context_score(row: LocalLibraryRow, normalized_query: str, context: LocalLibrarySearchContext) -> int:
    weights = _int_mapping(LOCAL_LIBRARY_RANKING_SPEC.get("context_weights"))
    row_type = normalize_search_text(context.type)
    item_type = normalize_search_text(row.type or row.category)
    source_sheet = normalize_search_text(row.source_sheet or row.category)
    expected_sheet = expected_library_sheet(row_type, context.travel_element)
    alias = matching_cross_type_alias(
        row,
        normalized_query,
        row_type=row_type,
        expected_sheet=expected_sheet,
    )

    score = 0
    if expected_sheet and source_sheet:
        if source_sheet == expected_sheet:
            score += weights.get("sheet_exact", 0)
        elif alias is not None:
            score += weights.get("sheet_alias", 0)
        else:
            score += weights.get("sheet_mismatch", 0)

    if row_type and item_type:
        if item_type == row_type:
            score += weights.get("type_exact", 0)
        elif alias is not None:
            score += weights.get("type_alias", 0)
        elif item_type in row_type or row_type in item_type:
            score += weights.get("type_partial", 0)
        else:
            score += weights.get("type_mismatch", 0)

    row_text = normalize_search_text(" ".join((context.travel_element, context.supplier, context.comments)))
    country = normalize_search_text(row.country)
    supplier = normalize_search_text(row.supplier)
    context_supplier = normalize_search_text(context.supplier)
    if country and country in row_text:
        score += weights.get("country_in_context", 0)
    if supplier and context_supplier == supplier:
        score += weights.get("supplier_exact", 0)
    if supplier and supplier in row_text:
        score += weights.get("supplier_in_context", 0)
    return score


def _int_mapping(value: object) -> dict[str, int]:
    return {str(key): int(item or 0) for key, item in value.items()} if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


__all__ = [
    "LocalLibrarySearchContext",
    "LocalLibrarySearchResult",
    "library_result_label",
    "library_result_preview",
    "search_library_rows",
]
