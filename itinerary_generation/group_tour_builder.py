"""Package assembly for canonical group-tour contracts."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

from itinerary_generation.group_tour_accommodation_policy import _accommodation_policy, _policies
from itinerary_generation.group_tour_commercial_items import _commercial_item, _commercial_status
from itinerary_generation.group_tour_constants import _DECLARED_DURATION_RE, _MEETING_FIELD_RE, _URL_RE
from itinerary_generation.group_tour_day_parser import (
    _apply_package_accommodation_hints,
    build_group_tour_day,
    _day_candidates,
)
from itinerary_generation.group_tour_master_rows import (
    _group_style,
    _master_candidates,
    _master_description,
    _master_inclusions,
    _master_title,
    _package_pickup_time,
)
from itinerary_generation.group_tour_models import GroupTourPackage
from itinerary_generation.group_tour_row_helpers import _itinerary_day_number, _row_text, _source_row_id
from itinerary_generation.group_tour_text import _clean, _clean_strings, _field, _infer_season, _int, _normalize_season

def _package_id(title: str, source_name: str, master: Mapping[str, Any], day_rows: Sequence[Mapping[str, Any]]) -> str:
    payload = "|".join(
        (
            source_name,
            title,
            _source_row_id(master, source_name),
            *(_source_row_id(row, source_name) for row in day_rows),
        )
    )
    return f"group-tour-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def build_group_tour_package(
    rows: Iterable[Mapping[str, Any]],
    *,
    season: str = "",
    source_name: str = "",
    package_id: str = "",
) -> GroupTourPackage | None:
    """Build one canonical package from source-owned rows.

    Known facts are preserved.  Missing facts remain empty or receive an
    explicit warning; conflicting season/duration/day mappings are never
    silently repaired.
    """

    row_list = list(rows or ())
    masters = _master_candidates(row_list)
    if not masters:
        return None
    master = masters[0]
    master_source = _row_text(master)
    day_rows = _day_candidates(row_list, master)
    if not day_rows:
        return None

    title = _master_title(master_source, master)
    inclusions = _master_inclusions(master, master_source)
    day_segments = tuple(build_group_tour_day(row, inclusions, source_name) for row in day_rows)
    day_segments = _apply_package_accommodation_hints(day_segments, master_source, inclusions)
    declared_match = _DECLARED_DURATION_RE.search(title or master_source)
    declared_duration = int(declared_match.group(1)) if declared_match else 0
    observed_duration = len(day_segments)
    highest_package_day = max((day.package_day_number for day in day_segments), default=0)
    # Product duration is a package fact, not merely the number of day rows that
    # happened to be supplied.  This also prevents output such as "Day 6 of 4"
    # when a partial supplier export retains the declared six-day programme.
    duration = max(observed_duration, highest_package_day, declared_duration)
    itinerary_days = tuple(day.itinerary_day_number for day in day_segments if day.itinerary_day_number)
    itinerary_start = min(itinerary_days) if itinerary_days else _itinerary_day_number(master)
    itinerary_end = max(itinerary_days) if itinerary_days else itinerary_start + max(0, duration - 1)

    warnings: list[str] = []
    if len(masters) > 1:
        warnings.append("multiple_group_tour_master_rows")
    package_days = [day.package_day_number for day in day_segments]
    expected_days = list(range(1, duration + 1))
    if package_days != expected_days:
        warnings.append("group_tour_package_day_sequence_mismatch")
    if itinerary_days and itinerary_days != tuple(range(itinerary_start, itinerary_start + duration)):
        warnings.append("group_tour_itinerary_day_sequence_mismatch")
    if declared_duration and declared_duration != observed_duration:
        warnings.append("group_tour_declared_duration_conflict")

    explicit_season = _normalize_season(season)
    inferred_season = _infer_season(f"{title}\n{master_source}")
    if explicit_season != "unknown":
        package_season = explicit_season
        if inferred_season != "unknown" and inferred_season != explicit_season:
            warnings.append("group_tour_season_source_conflict")
    else:
        package_season = inferred_season

    status, reason = _commercial_status(master, day_rows)
    accommodation = _accommodation_policy(master_source, inclusions, duration, day_segments)
    transport_policy, guide_policy = _policies(inclusions)
    commercial_items = tuple(
        item
        for item in (_commercial_item(row, source_name) for row in row_list)
        if item is not None
    )
    source_ids = _clean_strings(
        (_source_row_id(master, source_name),)
        + tuple(_source_row_id(row, source_name) for row in day_rows)
    )
    source_url = _clean(master.get("url"))
    if not source_url:
        match = _URL_RE.search(master_source)
        source_url = match.group(0) if match else ""

    return GroupTourPackage(
        package_id=package_id or _package_id(title, source_name, master, day_rows),
        title=title,
        season=package_season,
        declared_duration_days=declared_duration,
        duration_days=duration,
        itinerary_start_day=itinerary_start,
        itinerary_end_day=itinerary_end,
        meeting_point=_field(_MEETING_FIELD_RE, master_source) or _clean(master.get("meeting_point")),
        pickup_time=_package_pickup_time(master, master_source),
        description=_master_description(master_source),
        package_inclusions=inclusions,
        accommodation_policy=accommodation,
        transport_policy=transport_policy,
        guide_policy=guide_policy,
        group_style=_group_style(f"{title}\n{master_source}"),
        commercial_status=status,
        commercial_reason=reason,
        source_url=source_url,
        day_segments=day_segments,
        commercial_items=commercial_items,
        source_row_ids=source_ids,
        source_title=_clean(master.get("original_title") or master.get("travel_element") or master.get("title")),
        warnings=_clean_strings(warnings),
    )
