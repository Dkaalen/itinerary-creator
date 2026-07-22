"""Date-derived seasonal metadata for day-intro decisions.

Season is recorded only when an explicit row date is available.  Marketing
text is never used to infer day-intro season.
"""
from __future__ import annotations

from dataclasses import dataclass

from itinerary_generation.cover_season import _parse_date, _season_for_date
from itinerary_generation.day_facts import DayFacts


@dataclass(frozen=True)
class DayIntroSeasonalContext:
    season: str = ""
    source_date: str = ""


def seasonal_context_for(facts: DayFacts) -> DayIntroSeasonalContext:
    for row in facts.rows:
        for key in ("date", "start_date", "end_date"):
            raw = str(row.get(key, "") or "").strip()
            parsed = _parse_date(raw)
            if parsed is not None:
                return DayIntroSeasonalContext(_season_for_date(parsed), raw)
    return DayIntroSeasonalContext()
