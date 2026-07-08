"""Schedule Brain.

Understands the shape of a day: timed activities, gaps, evening work, and false
"rest of day open" cases. It produces facts only, not full prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from itinerary_generation.common import get_row_type
from itinerary_generation.day_timeline_events import clean_event_text
from itinerary_generation.title_decision_contract import select_activity_title
from text_polish import polish_title

_TIME_RE = re.compile(r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<suffix>am|pm)\b", re.IGNORECASE)


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
    flags: frozenset[str] = frozenset()


def _minutes_from_match(match: re.Match[str]) -> int:
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or "0")
    suffix = match.group("suffix").lower()
    if suffix == "pm" and hour != 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    return hour * 60 + minute


def _time_bounds(row: Mapping[str, object]) -> tuple[int | None, int | None]:
    source = " ".join(str(row.get(key) or "") for key in ("time", "display_time", "details", "original_title", "title"))
    matches = list(_TIME_RE.finditer(source))
    if not matches:
        return None, None
    start = _minutes_from_match(matches[0])
    end = _minutes_from_match(matches[1]) if len(matches) > 1 else None
    if end is not None and end < start:
        end += 24 * 60
    return start, end


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
        start, end = _time_bounds(row)
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
    sorted_timed = sorted(timed_activities, key=lambda event: event.start_minutes or 0)
    has_gap = False
    for first, second in zip(sorted_timed, sorted_timed[1:]):
        if first.end_minutes is not None and second.start_minutes is not None and second.start_minutes - first.end_minutes >= 90:
            has_gap = True
            break

    flags: set[str] = set()
    if has_activity_after_leisure:
        flags.add("activity_after_leisure")
    if has_leisure_between_activities:
        flags.add("leisure_between_activities")
    if has_gap:
        flags.add("gap_between_activities")
    if len(activities) >= 2:
        flags.add("multiple_activities")

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
        flags=frozenset(flags),
    )


__all__ = ["DayScheduleProfile", "ScheduleEvent", "build_day_schedule_profile"]
