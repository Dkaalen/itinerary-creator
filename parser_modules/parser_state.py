"""Mutable parser state for top-level row orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from parser_modules.common import normalize_type
from parser_modules.contextual_city import apply_context_city, context_city_from_row

_CONTEXT_ELIGIBLE_TYPES = {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry", "Leisure"}


@dataclass
class ParserState:
    current_day: str = ""
    last_context_city: str = ""
    day_context_city: dict[str, str] = field(default_factory=dict)
    pending_city_rows_by_day: dict[str, list[dict]] = field(default_factory=dict)
    seen_row_ids: set[str] = field(default_factory=set)

    def update_day(self, day: str) -> None:
        self.current_day = day

    def has_seen(self, row_id: str) -> bool:
        return row_id in self.seen_row_ids

    def remember_row_id(self, row_id: str) -> None:
        self.seen_row_ids.add(row_id)

    def apply_context(self, row: dict) -> None:
        context_city = self.day_context_city.get(self.current_day) or self.last_context_city
        apply_context_city(row, context_city)

    def register_row_context(self, row: dict, item_type: str) -> None:
        row_context_city = context_city_from_row(row)
        if row_context_city:
            self.day_context_city[self.current_day] = row_context_city
            self.last_context_city = row_context_city
            for pending_row in self.pending_city_rows_by_day.pop(self.current_day, []):
                apply_context_city(pending_row, row_context_city)
            return

        if normalize_type(item_type) in _CONTEXT_ELIGIBLE_TYPES:
            self.pending_city_rows_by_day.setdefault(self.current_day, []).append(row)
