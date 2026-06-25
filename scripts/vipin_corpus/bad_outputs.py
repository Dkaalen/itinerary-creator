"""Bad-output classification for Vipin corpus rows."""

from __future__ import annotations

import re
from typing import Any, Mapping

from scripts.vipin_corpus.constants import ALLOWED_EMPTY_TITLE_TYPES, DATEISH_RE, NON_ITINERARY_TYPES, TITLE_PROSE_MARKERS
from scripts.vipin_corpus.models import BadOutput, ExcelCorpusItem
from scripts.vipin_corpus.text import _norm, _norm_key, _number_like


def _bad(item: ExcelCorpusItem, category: str, reason: str, row: Mapping[str, Any] | None = None, generated_title: str = "") -> BadOutput:
    row = row or {}
    return BadOutput(
        source_id=item.source_id,
        category=category,
        reason=reason,
        source_type=item.row_type,
        source_day=item.day,
        source_city=item.city,
        source_date=item.from_date or item.to_date,
        parsed_type=str(row.get("type", "") or ""),
        effective_type=str(row.get("effective_type", "") or ""),
        parsed_city=str(row.get("city", "") or ""),
        parsed_title=str(row.get("title", "") or ""),
        generated_title=generated_title,
        confidence=int(row.get("parser_confidence")) if str(row.get("parser_confidence", "")).isdigit() else None,
        flags=tuple(str(flag) for flag in (row.get("parser_review_flags") or [])),
        details_excerpt=_norm(str(row.get("details", "") or item.element))[:280],
    )


def _source_missing_categories(item: ExcelCorpusItem) -> list[BadOutput]:
    categories: list[BadOutput] = []
    if not item.day:
        categories.append(_bad(item, "missing_source_day", "Source row has no day value."))
    if not item.row_type:
        categories.append(_bad(item, "missing_source_type", "Source row has no type value."))
    elif _norm_key(item.row_type) in NON_ITINERARY_TYPES:
        categories.append(_bad(item, "non_itinerary_type", "Source row type looks like a calculator/cost row."))
    if not item.city:
        categories.append(_bad(item, "missing_source_city", "Source row has no city/area value."))
    if not (item.from_date or item.to_date or DATEISH_RE.search(item.element)):
        categories.append(_bad(item, "missing_source_date", "Source row has no date value."))
    return categories


def _has_usable_source_content(item: ExcelCorpusItem) -> bool:
    """Return True when a source row has client-facing content to parse."""

    return bool(_norm(item.element) or _norm(item.city))


def _looks_report_only_source(item: ExcelCorpusItem) -> bool:
    """Return True for headers/calculator rows that should not parse as itinerary."""

    day = _norm_key(item.day)
    row_type = _norm_key(item.row_type)
    city = _norm_key(item.city)
    element = _norm_key(item.element)
    from_date = _norm_key(item.from_date)
    to_date = _norm_key(item.to_date)

    if {day, row_type, city} >= {"id", "day", "supplier"}:
        return True
    if row_type in NON_ITINERARY_TYPES or row_type in {"single room cost"}:
        return True
    if _number_like(day) and (_number_like(row_type) or "pricing" in from_date or "pricing" in to_date):
        return True
    if "cost per person" in day or "single room cost" in row_type:
        return True
    if "pricing" in from_date or "pricing" in to_date or "travels free" in from_date or "travels free" in to_date:
        return True
    if not (element or city) and (_number_like(day) or _number_like(row_type)):
        return True
    return False


def _looks_like_activity_prose_title(title: str) -> bool:
    title = _norm(title)
    if not title:
        return False
    if TITLE_PROSE_MARKERS.search(title):
        return True
    if len(title) >= 120 and re.search(r"[.!?]", title):
        return True
    if len(title.split()) >= 18 and re.search(r"\b(and|with|including|where|while|before|after)\b", title, flags=re.IGNORECASE):
        return True
    return False


def _row_output_categories(item: ExcelCorpusItem, row: Mapping[str, Any], generated_title: str = "") -> list[BadOutput]:
    categories: list[BadOutput] = []
    row_type = str(row.get("effective_type") or row.get("type") or "")
    title = _norm(row.get("title", ""))
    output_title = _norm(generated_title or title)
    city = _norm(row.get("city", ""))
    flags = set(row.get("parser_review_flags") or [])

    if not title and row_type not in ALLOWED_EMPTY_TITLE_TYPES:
        categories.append(_bad(item, "blank_title", "Parsed row has a blank title.", row, output_title))
    if len(title) > 100:
        categories.append(_bad(item, "overlong_title", "Parsed title is over 100 characters.", row, output_title))
    if _looks_like_activity_prose_title(title):
        categories.append(_bad(item, "activity_text_used_as_title", "Parsed title looks like supplier prose or activity body text.", row, output_title))
    if output_title and output_title != title:
        if len(output_title) > 100:
            categories.append(_bad(item, "overlong_generated_title", "Generated editable title is over 100 characters.", row, output_title))
        if _looks_like_activity_prose_title(output_title):
            categories.append(_bad(item, "activity_text_used_as_generated_title", "Generated editable title looks like supplier prose.", row, output_title))
    if row_type in {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry"} and not city and "missing_city" in flags:
        categories.append(_bad(item, "missing_parsed_city", "Parsed row is missing city/area.", row, output_title))
    if not row.get("type"):
        categories.append(_bad(item, "missing_parsed_type", "Parsed row is missing type.", row, output_title))
    if "missing_activity_title" in flags:
        categories.append(_bad(item, "missing_activity_title", "Parser flagged missing activity title.", row, output_title))
    return categories
