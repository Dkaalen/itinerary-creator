"""Minimal mutable state for raw parser row orchestration.

Raw parsing tracks day and duplicate source identity only. Geographic context
belongs to itinerary normalization, where route-aware facts are available.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParserState:
    current_day: str = ""
    seen_row_ids: set[str] = field(default_factory=set)

    def update_day(self, day: str) -> None:
        self.current_day = day

    def has_seen(self, row_id: str) -> bool:
        return row_id in self.seen_row_ids

    def remember_row_id(self, row_id: str) -> None:
        self.seen_row_ids.add(row_id)
