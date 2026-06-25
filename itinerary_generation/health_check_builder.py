"""Orchestrate actionable health issues from parsed itinerary facts."""

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

from itinerary_generation.common import group_rows_by_day
from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.destination_registry import destination_for_alias
from itinerary_generation.health_check_destinations import destination_review_values, is_reviewable_destination
from itinerary_generation.health_check_models import CRITICAL, REVIEW, INFO, CONTENT_TYPES, TRANSFER_TYPES, DAY_OVERFLOW_SERVICE_LIMIT, DAY_OVERFLOW_TEXT_LIMIT, HEAVY_ACTIVITY_LIMIT, ItineraryHealthIssue, ItineraryHealthSummary
from itinerary_generation.health_check_rows import day_text_weight, has_hotel_name, is_main_row, normalise_fingerprint, primary_day_city, route_endpoint, row_city, row_day, row_fingerprint, row_text, rows_list
from itinerary_generation.row_filters import get_row_type


def _issue(code, severity, message, row=None):
    row = row or {}
    return ItineraryHealthIssue(code, severity, message, row_day(row), row_city(row), get_row_type(row) if row else "")


def _row_issues(row):
    issues = []; row_type = get_row_type(row); day = row_day(row) or "Unknown day"; city = row_city(row)
    for _label, value in destination_review_values(row):
        if is_reviewable_destination(value) and destination_for_alias(value) is None:
            issues.append(_issue("unknown_destination", REVIEW, f"{day}: {value} is not in the Nordic destination registry; confirm spelling or add this destination before final output.", row)); break
    if row_type == "Hotel" and not has_hotel_name(row): issues.append(_issue("missing_hotel_name", CRITICAL, f"{day}: hotel row is missing a hotel name.", row))
    if row_type in TRANSFER_TYPES:
        has_route = bool(route_endpoint(row, destination=False) and route_endpoint(row, destination=True))
        if not row_text(row, "details", "description", "route", "title", "original_title") or not has_route: issues.append(_issue("missing_transfer_route", REVIEW, f"{day}: {row_type} needs clearer origin/destination details.", row))
    if row_type != "Hotel" and not city and row_type in {"Activity", "Transfer", "Train", "Cruise", "Ferry"}: issues.append(_issue("missing_city", REVIEW, f"{day}: {row_type} is missing a city or area.", row))
    return issues


def _day_issues(grouped):
    issues, ordered_cities = [], []
    for day, rows in grouped.items():
        counts = Counter(get_row_type(row) for row in rows); total = sum(1 for row in rows if get_row_type(row) in CONTENT_TYPES)
        if total >= DAY_OVERFLOW_SERVICE_LIMIT or counts.get("Activity", 0) >= HEAVY_ACTIVITY_LIMIT or day_text_weight(rows) >= DAY_OVERFLOW_TEXT_LIMIT: issues.append(ItineraryHealthIssue("busy_day_pdf_risk", REVIEW, f"{day}: many services or long descriptions may overflow one A4 page; review layout before export.", day=str(day), row_type="Day", source="layout_preflight"))
        if counts.get("Hotel", 0) > 1: issues.append(ItineraryHealthIssue("multiple_hotels_same_day", REVIEW, f"{day}: multiple hotel rows appear on the same day; confirm this is intentional.", day=str(day), row_type="Hotel", source="day_structure"))
        if sum(counts.get(kind, 0) for kind in TRANSFER_TYPES) >= 3 and counts.get("Activity", 0) >= 1: issues.append(ItineraryHealthIssue("transport_heavy_day", REVIEW, f"{day}: several transfers plus activities may be unrealistic for one day.", day=str(day), row_type="Day", source="route_sanity"))
        city = primary_day_city(rows)
        if city: ordered_cities.append((str(day), city))
    positions = defaultdict(list)
    for index, (_day, city) in enumerate(ordered_cities): positions[normalise_fingerprint(city)].append(index)
    for indexes in positions.values():
        if len(indexes) >= 2 and any((b-a) > 1 for a,b in zip(indexes,indexes[1:])):
            city = ordered_cities[indexes[0]][1]; issues.append(ItineraryHealthIssue("route_backtrack", INFO, f"Route returns to {city} after other destinations; confirm the routing is intentional.", city=city, row_type="Route", source="route_sanity"))
    return issues


def build_itinerary_health_issues(parsed_rows: Iterable[Mapping[str, Any]] | None, *, parser_diagnostics: Iterable[Mapping[str, Any]] | None = None) -> tuple[ItineraryHealthIssue, ...]:
    rows = rows_list(parsed_rows); main = [row for row in rows if is_main_row(row)]; issues = [issue for row in main for issue in _row_issues(row)]
    duplicates = defaultdict(list)
    for row in main:
        fingerprint = row_fingerprint(row)
        if fingerprint and fingerprint.count("|") == 2: duplicates[(row_day(row), fingerprint)].append(row)
    for group in duplicates.values():
        if len(group) >= 2: issues.append(_issue("duplicate_service", REVIEW, f"{row_day(group[0]) or 'Unknown day'}: possible duplicate {get_row_type(group[0]).lower()} service detected.", group[0]))
    issues.extend(_day_issues(group_rows_by_day(main)))
    day_numbers = sorted({get_day_number(row.get("day", "")) for row in main if get_day_number(row.get("day", ""))})
    if day_numbers:
        missing = sorted(set(range(day_numbers[0], day_numbers[-1]+1)) - set(day_numbers))
        if missing: issues.append(ItineraryHealthIssue("missing_day_numbers", REVIEW, f"Generated structure skips day number(s): {', '.join(str(day) for day in missing)}.", source="day_sequence"))
    for diagnostic in parser_diagnostics or []:
        message = str(diagnostic.get("message", "") if isinstance(diagnostic, Mapping) else diagnostic).strip(); category = str(diagnostic.get("category", "parser") if isinstance(diagnostic, Mapping) else "parser").strip()
        if message: issues.append(ItineraryHealthIssue(f"parser_{category or 'notice'}", INFO, f"Parser notice: {message}", source="parser_diagnostics"))
    unique, seen = [], set()
    for issue in issues:
        key = (issue.code, issue.day, issue.city, issue.message)
        if key not in seen: seen.add(key); unique.append(issue)
    return tuple(unique)


def summarize_itinerary_health_issues(issues: Iterable[ItineraryHealthIssue]) -> ItineraryHealthSummary:
    counts = Counter(issue.severity for issue in issues)
    return ItineraryHealthSummary(counts.get(CRITICAL,0), counts.get(REVIEW,0), counts.get(INFO,0), sum(counts.values()))
