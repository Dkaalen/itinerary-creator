"""Schedule Brain.

Understands the shape of a day: timed activities, gaps, evening work, and false
"rest of day open" cases. It produces facts only, not full prose.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

from itinerary_generation.common import get_row_type
from itinerary_generation.day_timeline_events import clean_event_text
from itinerary_generation.schedule_occupancy import DayScheduleOccupancy, analyze_schedule_occupancy
from itinerary_generation.schedule_time_ranges import parse_time_range
from itinerary_generation.title_decision_contract import select_activity_title
from text_polish import polish_title

@dataclass(frozen=True)
class ScheduleEvent:
    order: int
    row_type: str
    title: str = ""
    start_minutes: int | None = None
    end_minutes: int | None = None
    period: str = ""
    is_activity: bool = False
    is_leisure: bool = False
    is_transport: bool = False
    has_invalid_time_range: bool = False
    crosses_midnight: bool = False


@dataclass(frozen=True)
class DayScheduleProfile:
    events: tuple[ScheduleEvent, ...] = ()
    activity_count: int = 0
    timed_activity_count: int = 0
    leisure_count: int = 0
    has_morning_activity: bool = False
    has_afternoon_activity: bool = False
    has_evening_activity: bool = False
    has_late_night_activity: bool = False
    has_multiple_arranged_activities: bool = False
    has_activity_after_leisure: bool = False
    has_leisure_between_activities: bool = False
    has_gap_between_activities: bool = False
    first_activity_title: str = ""
    last_activity_title: str = ""
    shape: str = "simple"
    occupancy: DayScheduleOccupancy = DayScheduleOccupancy()
    flags: frozenset[str] = frozenset()


def _period(start: int | None) -> str:
    if start is None:
        return "flexible"
    hour = (start // 60) % 24
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def _activity_title(row: Mapping[str, object]) -> str:
    # Title Brain owns activity-title source priority. Schedule Brain only needs
    # the selected title as a schedule fact, never its own fallback hierarchy.
    return clean_event_text(select_activity_title(row).text or "Experience")


def _is_blank_leisure_activity(row: Mapping[str, object]) -> bool:
    text = clean_event_text(" ".join(str(row.get(key) or "") for key in ("title", "original_title", "details"))).lower()
    return bool(re.fullmatch(r"(?:[a-zøåäö .'-]+:\s*)?(?:spend time at leisure|leisure|free time)\.?", text.strip()))


def build_day_schedule_profile(rows: Sequence[Mapping[str, object]] | None) -> DayScheduleProfile:
    events: list[ScheduleEvent] = []
    for index, row in enumerate(rows or []):
        if not isinstance(row, Mapping):
            continue
        row_type = get_row_type(dict(row))
        is_activity = row_type == "Activity" and not _is_blank_leisure_activity(row)
        is_leisure = row_type == "Leisure" or (row_type == "Activity" and _is_blank_leisure_activity(row))
        is_transport = row_type in {"Transfer", "Train", "Flight", "Cruise", "Ferry", "Transport", "Coach", "Bus"}
        time_source = " ".join(str(row.get(key) or "") for key in ("time", "display_time", "details", "original_title", "title"))
        time_range = parse_time_range(time_source)
        start, end = time_range.start_minutes, time_range.end_minutes
        title = _activity_title(row) if is_activity else polish_title(str(row.get("title") or row.get("original_title") or ""))
        events.append(
            ScheduleEvent(
                order=index,
                row_type=row_type,
                title=title,
                start_minutes=start,
                end_minutes=end,
                period=_period(start),
                is_activity=is_activity,
                is_leisure=is_leisure,
                is_transport=is_transport,
                has_invalid_time_range=time_range.is_invalid,
                crosses_midnight=time_range.is_overnight,
            )
        )

    activities = [event for event in events if event.is_activity]
    timed_activities = [event for event in activities if event.start_minutes is not None]
    leisure_events = [event for event in events if event.is_leisure]
    has_activity_after_leisure = any(
        activity.order > leisure.order for leisure in leisure_events for activity in activities
    )
    has_leisure_between_activities = any(
        any(before.order < leisure.order < after.order for before in activities for after in activities if before.order < after.order)
        for leisure in leisure_events
    )
    occupancy = analyze_schedule_occupancy(events)
    has_gap = occupancy.longest_gap_minutes >= 90

    flags: set[str] = set()
    if has_activity_after_leisure:
        flags.add("activity_after_leisure")
    if has_leisure_between_activities:
        flags.add("leisure_between_activities")
    if has_gap:
        flags.add("gap_between_activities")
    if len(activities) >= 2:
        flags.add("multiple_activities")
    if occupancy.is_full_day:
        flags.add("full_day_schedule")
    if occupancy.finishes_late:
        flags.add("late_finish")
    if occupancy.has_invalid_time_range:
        flags.add("invalid_time_range")

    shape = "simple"
    if len(activities) >= 2 and (has_leisure_between_activities or has_gap):
        shape = "activity_gap_activity"
    elif len(activities) >= 2:
        shape = "multi_activity"
    elif activities and any(event.is_transport for event in events):
        shape = "travel_activity"
    elif activities:
        shape = "activity"

    return DayScheduleProfile(
        events=tuple(events),
        activity_count=len(activities),
        timed_activity_count=len(timed_activities),
        leisure_count=len(leisure_events),
        has_morning_activity=any(event.period == "morning" for event in timed_activities),
        has_afternoon_activity=any(event.period == "afternoon" for event in timed_activities),
        has_evening_activity=any(event.period == "evening" for event in timed_activities),
        has_late_night_activity=any((event.end_minutes or 0) >= 24 * 60 for event in timed_activities),
        has_multiple_arranged_activities=len(activities) >= 2,
        has_activity_after_leisure=has_activity_after_leisure,
        has_leisure_between_activities=has_leisure_between_activities,
        has_gap_between_activities=has_gap,
        first_activity_title=activities[0].title if activities else "",
        last_activity_title=activities[-1].title if activities else "",
        shape=shape,
        occupancy=occupancy,
        flags=frozenset(flags),
    )


__all__ = ["DayScheduleProfile", "ScheduleEvent", "build_day_schedule_profile"]
