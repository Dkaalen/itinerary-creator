"""Row annotation and metadata hydration helpers for group tours."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from itinerary_generation.group_tour_builder import build_group_tour_package
from itinerary_generation.group_tour_day_parser import _day_candidates, _package_day_parts
from itinerary_generation.group_tour_master_rows import _master_candidates
from itinerary_generation.group_tour_models import GroupTourDay, GroupTourPackage
from itinerary_generation.group_tour_row_helpers import _group_tour_day_source

def annotate_group_tour_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    season: str = "",
    source_name: str = "",
) -> list[dict[str, Any]]:
    """Attach the package contract and day references without changing output.

    The package metadata is attached only to the master row.  Daily rows receive
    the matching day-segment metadata and package ID.  Independent pre/post
    hotels and commercial add-ons remain separate rows.
    """

    updated = [deepcopy(dict(row)) for row in rows or ()]
    package = build_group_tour_package(updated, season=season, source_name=source_name)
    if package is None:
        return updated

    masters = _master_candidates(updated)
    day_rows = _day_candidates(updated, masters[0]) if masters else []
    if masters:
        master = masters[0]
        master["group_tour_package"] = package.as_metadata
        master["group_tour_package_id"] = package.package_id
    segments = {day.package_day_number: day for day in package.day_segments}
    for row in day_rows:
        package_day, _, _, _ = _package_day_parts(_group_tour_day_source(row))
        segment = segments.get(package_day)
        if segment is None:
            continue
        row["group_tour_package_id"] = package.package_id
        row["group_tour_day"] = segment.as_metadata
    return updated


def group_tour_package_from_row(row: Mapping[str, Any] | None) -> GroupTourPackage | None:
    if not row:
        return None
    value = row.get("group_tour_package")
    if not isinstance(value, Mapping):
        return None
    try:
        return GroupTourPackage.from_metadata(value)
    except (TypeError, ValueError):
        return None


def group_tour_day_from_row(row: Mapping[str, Any] | None) -> GroupTourDay | None:
    if not row:
        return None
    value = row.get("group_tour_day")
    if not isinstance(value, Mapping):
        return None
    try:
        return GroupTourDay.from_metadata(value)
    except (TypeError, ValueError):
        return None


