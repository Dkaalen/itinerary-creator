"""Derive usable-time facts from arranged schedule events.

Schedule occupancy is factual only.  Copy writers consume these facts but do
not recalculate duration, late finish, or full-day status independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class DayScheduleOccupancy:
    first_start_minutes: int | None = None
    last_end_minutes: int | None = None
    arranged_minutes: int = 0
    arranged_span_minutes: int = 0
    longest_gap_minutes: int = 0
    has_invalid_time_range: bool = False
    is_full_day: bool = False
    finishes_late: bool = False
    has_meaningful_post_activity_time: bool = True


def analyze_time_intervals(
    intervals: Sequence[tuple[int, int]],
    *,
    has_invalid_time_range: bool = False,
) -> DayScheduleOccupancy:
    """Return occupancy for validated clock intervals.

    Intervals are merged before duration is calculated so overlapping
    activities cannot be double-counted by Schedule Brain or final-output QA.
    """

    valid = sorted((int(start), int(end)) for start, end in intervals if end >= start)
    if not valid:
        return DayScheduleOccupancy(has_invalid_time_range=has_invalid_time_range)

    merged: list[list[int]] = []
    for start, end in valid:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
            continue
        merged[-1][1] = max(merged[-1][1], end)

    first_start = merged[0][0]
    last_end = merged[-1][1]
    arranged = sum(max(0, end - start) for start, end in merged)
    span = max(0, last_end - first_start)
    gaps = [max(0, second[0] - first[1]) for first, second in zip(merged, merged[1:])]
    longest_gap = max(gaps, default=0)
    full_day = arranged >= 8 * 60 or span >= 9 * 60
    local_end = last_end % (24 * 60)
    finishes_late = last_end >= 24 * 60 or local_end >= 18 * 60
    meaningful_after = not full_day and not finishes_late and local_end <= 17 * 60
    return DayScheduleOccupancy(
        first_start_minutes=first_start,
        last_end_minutes=last_end,
        arranged_minutes=arranged,
        arranged_span_minutes=span,
        longest_gap_minutes=longest_gap,
        has_invalid_time_range=has_invalid_time_range,
        is_full_day=full_day,
        finishes_late=finishes_late,
        has_meaningful_post_activity_time=meaningful_after,
    )


def analyze_schedule_occupancy(events: Iterable[object]) -> DayScheduleOccupancy:
    activity_events = [event for event in events if bool(getattr(event, "is_activity", False))]
    timed = [
        event
        for event in activity_events
        if getattr(event, "start_minutes", None) is not None
        and getattr(event, "end_minutes", None) is not None
        and not bool(getattr(event, "has_invalid_time_range", False))
    ]
    invalid = any(bool(getattr(event, "has_invalid_time_range", False)) for event in activity_events)
    intervals = [
        (int(getattr(event, "start_minutes")), int(getattr(event, "end_minutes")))
        for event in timed
    ]
    return analyze_time_intervals(intervals, has_invalid_time_range=invalid)


__all__ = ["DayScheduleOccupancy", "analyze_schedule_occupancy", "analyze_time_intervals"]
