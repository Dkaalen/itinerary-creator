"""Resolve canonical group-tour package and day context from rows."""

from typing import Any, Iterable, Mapping

from itinerary_generation.group_tour_domain import GroupTourDay, GroupTourPackage, group_tour_day_from_row, group_tour_package_from_row


def group_tour_package_from_rows(rows: Iterable[Mapping[str, Any]]) -> GroupTourPackage | None:
    for row in rows or ():
        package = group_tour_package_from_row(row)
        if package is not None: return package
    return None


def group_tour_day_from_rows(rows: Iterable[Mapping[str, Any]]) -> GroupTourDay | None:
    for row in rows or ():
        segment = group_tour_day_from_row(row)
        if segment is not None: return segment
    return None


def group_tour_package_context_from_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    for row in rows or ():
        value = row.get("group_tour_package_context")
        if isinstance(value, Mapping): return dict(value)
    package = group_tour_package_from_rows(rows)
    if package is None: return {}
    return {"package_id": package.package_id, "title": package.title, "season": package.season, "duration_days": package.duration_days, "itinerary_start_day": package.itinerary_start_day, "itinerary_end_day": package.itinerary_end_day, "meeting_point": package.meeting_point, "pickup_time": package.pickup_time, "group_style": package.group_style, "commercial_status": package.commercial_status, "accommodation_policy": package.accommodation_policy.as_metadata, "warnings": list(package.warnings)}
