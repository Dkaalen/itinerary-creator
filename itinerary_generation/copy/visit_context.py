"""Itinerary-level visit context for deterministic day copy."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from itinerary_generation.common import get_primary_city
from itinerary_generation.destination_registry import destination_for_alias
from text_polish import polish_title


@dataclass(frozen=True)
class DayVisitContext:
    """Visit information for one itinerary day.

    The copy engine uses this to avoid treating a repeated city as a first
    arrival.  It is deliberately small and fact-only so it can be passed through
    render/preview/PDF code without becoming another rendering model.
    """

    day: str = ""
    city: str = ""
    canonical_city: str = ""
    visit_number: int = 1
    previous_days: tuple[str, ...] = ()

    @property
    def is_return_visit(self) -> bool:
        return self.visit_number > 1 and bool(self.canonical_city)


def _canonical_city(value: object) -> str:
    text = polish_title(str(value or "").strip())
    if not text:
        return ""
    record = destination_for_alias(text)
    return record.name if record else text


def _day_sort_key(day: object, index: int) -> tuple[int, int, str]:
    text = str(day or "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return (int(digits) if digits else index + 1_000_000, index, text)


def build_day_visit_contexts(grouped_days: Mapping[str, Sequence[dict]] | Iterable[tuple[str, Sequence[dict]]]) -> dict[str, DayVisitContext]:
    """Return visit context keyed by day label for a grouped itinerary."""

    if isinstance(grouped_days, Mapping):
        items = list(grouped_days.items())
    else:
        items = list(grouped_days)
    indexed_items = list(enumerate(items))
    indexed_items.sort(key=lambda item: _day_sort_key(item[1][0], item[0]))

    seen: dict[str, list[str]] = defaultdict(list)
    contexts: dict[str, DayVisitContext] = {}
    for _, (day, rows) in indexed_items:
        day_label = str(day or "")
        city = polish_title(get_primary_city(rows or []) or "")
        canonical = _canonical_city(city)
        previous = tuple(seen[canonical]) if canonical else ()
        visit_number = len(previous) + 1 if canonical else 1
        contexts[day_label] = DayVisitContext(
            day=day_label,
            city=city,
            canonical_city=canonical,
            visit_number=visit_number,
            previous_days=previous,
        )
        if canonical:
            seen[canonical].append(day_label)
    return contexts
