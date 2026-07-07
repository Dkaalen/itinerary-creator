"""Schedule profile adapter for day facts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from itinerary_generation.schedule_brain import DayScheduleProfile, build_day_schedule_profile


def build_schedule_facts(rows: Sequence[Mapping[str, Any]]) -> DayScheduleProfile:
    """Return the Schedule Brain profile used by DayFacts."""

    return build_day_schedule_profile(rows)


__all__ = ["DayScheduleProfile", "build_schedule_facts"]
