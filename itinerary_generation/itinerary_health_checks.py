"""Actionable itinerary health checks used by review and export screens.

This module is deliberately presentation-free.  It turns the parsed row model
into a small set of consultant-facing issues that can be shown before styling,
picture review, or PDF export.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable, Mapping

from itinerary_generation.common import group_rows_by_day
from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.destination_registry import destination_for_alias
from itinerary_generation.row_filters import get_row_type, is_optional_row
from itinerary_generation.transport_safety import base_destination_from_terminal, normalize_transport_place

CRITICAL = "critical"
REVIEW = "review"
INFO = "info"

_CONTENT_TYPES = {
    "Activity",
    "Cruise",
    "Ferry",
    "Flight",
    "Hotel",
    "Rental Car",
    "Self Drive",
    "Train",
    "Transfer",
}
_TRANSFER_TYPES = {"Transfer", "Flight", "Train", "Ferry", "Cruise", "Rental Car", "Self Drive", "Transport"}
_DAY_OVERFLOW_TEXT_LIMIT = 2600
_DAY_OVERFLOW_SERVICE_LIMIT = 6
_HEAVY_ACTIVITY_LIMIT = 4

_DESTINATION_FIELD_TYPES = {"Activity", "Cruise", "Ferry", "Flight", "Hotel", "Train", "Transfer", "Transport", "Self Drive", "Rental Car"}
_DESTINATION_REVIEW_IGNORE = {
    "",
    "airport",
    "bus terminal",
    "cruise port",
    "hotel",
    "railway station",
    "station",
    "the accommodation",
    "your accommodation",
    "self transfer",
    "private transfer",
}


def _clean_destination_for_registry(value: object, *, strip_terminal: bool = True) -> str:
    text = normalize_transport_place(str(value or "").strip())
    text = re.sub(r"^(?:to|from|in|at)\s+", "", text, flags=re.IGNORECASE).strip(" -:|.,")
    text = re.sub(r"^(?:self|private)\s+transfer(?:\s+to)?\s*", "", text, flags=re.IGNORECASE).strip(" -:|.,")
    if strip_terminal:
        text = base_destination_from_terminal(text) or text
        text = re.sub(r"\b(?:train|rail|railway|bus|coach|cruise|ferry|airport)\s*$", "", text, flags=re.IGNORECASE).strip(" -:|.,")
    text = re.sub(r"\b(?:your|the)\s+accommodation\b", "", text, flags=re.IGNORECASE).strip(" -:|.,")
    return text


def _is_reviewable_destination(value: str) -> bool:
    text = str(value or "").strip()
    if len(text) < 3 or text.lower() in _DESTINATION_REVIEW_IGNORE:
        return False
    if not re.search(r"[A-Za-zÀ-ÿøØåÅäÄöÖðÐþÞ]", text):
        return False
    if re.search(r"\b(?:self transfer|private transfer|meeting point|platform|tickets?|breakfast|standard room|double room|fjord lounge)\b", text, flags=re.IGNORECASE):
        return False
    return True


def _destination_review_values(row: Mapping[str, Any]) -> list[tuple[str, str]]:
    row_type = get_row_type(row)
    values: list[tuple[str, str]] = []
    city = _city(row)
    if row_type in _DESTINATION_FIELD_TYPES and city:
        values.append(("city", city))
    if row_type in _TRANSFER_TYPES:
        origin = _route_endpoint(row, destination=False)
        destination = _route_endpoint(row, destination=True)
        if origin:
            values.append(("route origin", origin))
        if destination:
            values.append(("route destination", destination))
    clean: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for label, value in values:
        candidate = _clean_destination_for_registry(value, strip_terminal=label != "city")
        key = (label, candidate.lower())
        if candidate and key not in seen:
            seen.add(key)
            clean.append((label, candidate))
    return clean

@dataclass(frozen=True)
class ItineraryHealthIssue:
    """One actionable issue in the parsed itinerary model."""

    code: str
    severity: str
    message: str
    day: str = ""
    city: str = ""
    row_type: str = ""
    source: str = "parsed_rows"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ItineraryHealthSummary:
    """Small aggregate used by UI cards and export preflight."""

    critical: int
    review: int
    info: int
    total: int

    @property
    def status_label(self) -> str:
        if self.critical:
            return "Needs review"
        if self.review:
            return "Review"
        return "Clear"


def _rows(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(row) for row in rows or [] if isinstance(row, Mapping)]


def _text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _day(row: Mapping[str, Any]) -> str:
    return _text(row, "day", "day_label")


def _city(row: Mapping[str, Any]) -> str:
    return _text(row, "city", "destination", "location")


def _is_main_row(row: Mapping[str, Any]) -> bool:
    row_type = get_row_type(row)
    return row_type in _CONTENT_TYPES and not is_optional_row(row)


def _has_title(row: Mapping[str, Any]) -> bool:
    return bool(_text(row, "title", "original_title", "activity_title", "hotel_name", "name"))


def _has_hotel_name(row: Mapping[str, Any]) -> bool:
    return bool(_text(row, "hotel_name", "hotel", "accommodation", "title", "name"))


def _has_transfer_endpoint(row: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    return bool(_text(row, *keys))



def _normalise_fingerprint(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").lower()).strip()
    text = re.sub(r"[^a-z0-9à-ÿøåäö .'-]", "", text)
    return text[:160]


def _row_fingerprint(row: Mapping[str, Any]) -> str:
    row_type = get_row_type(row)
    title = _text(row, "title", "original_title", "hotel_name", "name")
    details = _text(row, "details", "description")
    city = _city(row)
    return "|".join([
        row_type,
        _normalise_fingerprint(city),
        _normalise_fingerprint(title or details),
    ])


def _route_endpoint(row: Mapping[str, Any], *, destination: bool) -> str:
    keys = (
        ("route_destination", "destination", "to", "to_city", "dropoff", "dropoff_place", "end_location")
        if destination
        else ("route_origin", "origin", "from", "from_city", "pickup", "pickup_place", "start_location")
    )
    value = _text(row, *keys)
    if value:
        return value

    source = " - ".join(_text(row, key) for key in ("title", "details", "description", "route", "original_title") if _text(row, key))
    match = re.search(r"\bfrom\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})(?:\s+-\s+|\s+\||,|$)", source, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\b(?:train|flight|coach|bus|ferry|cruise|transfer|private\s+transfer)\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})(?:\s+-\s+|\s+\||,|$)", source, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45})(?:\s+-\s+|\s+\||,|$)", source, flags=re.IGNORECASE)
    if not match:
        return ""
    raw = match.group(2 if destination else 1)
    raw = re.sub(r"^(?:train|flight|coach|bus|ferry|cruise|transfer|private\s+transfer)\s+", "", raw, flags=re.IGNORECASE)
    raw = re.split(r"\b(?:hotel|station|airport|time|departure|arrival|onboard|included)\b", raw, maxsplit=1, flags=re.IGNORECASE)[0]
    return raw.strip(" -:|.,")


def _day_text_weight(day_rows: Iterable[Mapping[str, Any]]) -> int:
    total = 0
    for row in day_rows:
        for key in ("title", "details", "description", "client_description"):
            total += len(str(row.get(key, "") or ""))
        for key in ("includes", "notable_sights"):
            value = row.get(key)
            if isinstance(value, (list, tuple)):
                total += sum(len(str(item or "")) for item in value)
    return total


def _primary_day_city(day_rows: Iterable[Mapping[str, Any]]) -> str:
    rows = list(day_rows)
    for row in rows:
        if get_row_type(row) == "Hotel" and _city(row):
            return _city(row)
    for row in rows:
        if get_row_type(row) in _TRANSFER_TYPES:
            destination = _route_endpoint(row, destination=True)
            if destination:
                return destination
    for row in rows:
        if _city(row):
            return _city(row)
    return ""

def _issue(code: str, severity: str, message: str, row: Mapping[str, Any] | None = None) -> ItineraryHealthIssue:
    row = row or {}
    return ItineraryHealthIssue(
        code=code,
        severity=severity,
        message=message,
        day=_day(row),
        city=_city(row),
        row_type=get_row_type(row) if row else "",
    )


def build_itinerary_health_issues(
    parsed_rows: Iterable[Mapping[str, Any]] | None,
    *,
    parser_diagnostics: Iterable[Mapping[str, Any]] | None = None,
) -> tuple[ItineraryHealthIssue, ...]:
    """Return deterministic, actionable health issues for the parsed model."""

    rows = _rows(parsed_rows)
    issues: list[ItineraryHealthIssue] = []
    main_rows = [row for row in rows if _is_main_row(row)]

    for row in main_rows:
        row_type = get_row_type(row)
        day = _day(row) or "Unknown day"
        city = _city(row)
        for value_label, destination_value in _destination_review_values(row):
            if not _is_reviewable_destination(destination_value):
                continue
            if destination_for_alias(destination_value) is None:
                issues.append(_issue(
                    "unknown_destination",
                    REVIEW,
                    f"{day}: {destination_value} is not in the Nordic destination registry; confirm spelling or add this destination before final output.",
                    row,
                ))
                break
        if row_type == "Hotel" and not _has_hotel_name(row):
            issues.append(_issue(
                "missing_hotel_name",
                CRITICAL,
                f"{day}: hotel row is missing a hotel name.",
                row,
            ))
        if row_type in _TRANSFER_TYPES:
            has_origin = bool(_route_endpoint(row, destination=False))
            has_destination = bool(_route_endpoint(row, destination=True))
            has_details = bool(_text(row, "details", "description", "route", "title", "original_title"))
            if not has_details or not (has_origin and has_destination):
                issues.append(_issue(
                    "missing_transfer_route",
                    REVIEW,
                    f"{day}: {row_type} needs clearer origin/destination details.",
                    row,
                ))
        if row_type != "Hotel" and not city and row_type in {"Activity", "Transfer", "Train", "Cruise", "Ferry"}:
            issues.append(_issue(
                "missing_city",
                REVIEW,
                f"{day}: {row_type} is missing a city or area.",
                row,
            ))

    grouped = group_rows_by_day(main_rows)
    duplicate_rows: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in main_rows:
        fingerprint = _row_fingerprint(row)
        if fingerprint and fingerprint.count("|") == 2:
            duplicate_rows[(str(_day(row)), fingerprint)].append(row)

    for (_day_key, _fingerprint), duplicate_group in duplicate_rows.items():
        if len(duplicate_group) < 2:
            continue
        sample = duplicate_group[0]
        issues.append(_issue(
            "duplicate_service",
            REVIEW,
            f"{_day(sample) or 'Unknown day'}: possible duplicate {get_row_type(sample).lower()} service detected.",
            sample,
        ))

    ordered_day_cities: list[tuple[str, str]] = []
    for day, day_rows in grouped.items():
        counts = Counter(get_row_type(row) for row in day_rows)
        total = sum(1 for row in day_rows if get_row_type(row) in _CONTENT_TYPES)
        text_weight = _day_text_weight(day_rows)
        if total >= _DAY_OVERFLOW_SERVICE_LIMIT or counts.get("Activity", 0) >= _HEAVY_ACTIVITY_LIMIT or text_weight >= _DAY_OVERFLOW_TEXT_LIMIT:
            issues.append(ItineraryHealthIssue(
                code="busy_day_pdf_risk",
                severity=REVIEW,
                message=f"{day}: many services or long descriptions may overflow one A4 page; review layout before export.",
                day=str(day),
                row_type="Day",
                source="layout_preflight",
            ))
        if counts.get("Hotel", 0) > 1:
            issues.append(ItineraryHealthIssue(
                code="multiple_hotels_same_day",
                severity=REVIEW,
                message=f"{day}: multiple hotel rows appear on the same day; confirm this is intentional.",
                day=str(day),
                row_type="Hotel",
                source="day_structure",
            ))
        if sum(counts.get(kind, 0) for kind in _TRANSFER_TYPES) >= 3 and counts.get("Activity", 0) >= 1:
            issues.append(ItineraryHealthIssue(
                code="transport_heavy_day",
                severity=REVIEW,
                message=f"{day}: several transfers plus activities may be unrealistic for one day.",
                day=str(day),
                row_type="Day",
                source="route_sanity",
            ))
        primary_city = _primary_day_city(day_rows)
        if primary_city:
            ordered_day_cities.append((str(day), primary_city))

    city_positions: defaultdict[str, list[int]] = defaultdict(list)
    for index, (_day_label, city) in enumerate(ordered_day_cities):
        city_positions[_normalise_fingerprint(city)].append(index)
    for city_key, positions in city_positions.items():
        if len(positions) >= 2 and any((b - a) > 1 for a, b in zip(positions, positions[1:])):
            city = ordered_day_cities[positions[0]][1]
            issues.append(ItineraryHealthIssue(
                code="route_backtrack",
                severity=INFO,
                message=f"Route returns to {city} after other destinations; confirm the routing is intentional.",
                city=city,
                row_type="Route",
                source="route_sanity",
            ))

    day_numbers = sorted({get_day_number(row.get("day", "")) for row in main_rows if get_day_number(row.get("day", ""))})
    if day_numbers:
        expected = set(range(day_numbers[0], day_numbers[-1] + 1))
        missing = sorted(expected - set(day_numbers))
        if missing:
            issues.append(ItineraryHealthIssue(
                code="missing_day_numbers",
                severity=REVIEW,
                message=f"Generated structure skips day number(s): {', '.join(str(day) for day in missing)}.",
                source="day_sequence",
            ))

    for diagnostic in parser_diagnostics or []:
        message = str(diagnostic.get("message", "") if isinstance(diagnostic, Mapping) else diagnostic).strip()
        category = str(diagnostic.get("category", "parser") if isinstance(diagnostic, Mapping) else "parser").strip()
        if message:
            issues.append(ItineraryHealthIssue(
                code=f"parser_{category or 'notice'}",
                severity=INFO,
                message=f"Parser notice: {message}",
                source="parser_diagnostics",
            ))

    seen: set[tuple[str, str, str, str]] = set()
    unique: list[ItineraryHealthIssue] = []
    for issue in issues:
        key = (issue.code, issue.day, issue.city, issue.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return tuple(unique)


def summarize_itinerary_health_issues(issues: Iterable[ItineraryHealthIssue]) -> ItineraryHealthSummary:
    counts = Counter(issue.severity for issue in issues)
    total = sum(counts.values())
    return ItineraryHealthSummary(
        critical=counts.get(CRITICAL, 0),
        review=counts.get(REVIEW, 0),
        info=counts.get(INFO, 0),
        total=total,
    )
