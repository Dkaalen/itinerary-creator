"""Build row-level structured input review records."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from itinerary_generation.destination_registry import destination_for_alias
from itinerary_generation.input_review_helpers import _confidence, _rows, _text
from itinerary_generation.input_review_models import StructuredInputRowReview
from itinerary_generation.row_filters import get_row_type


def _missing_fields(flags: Iterable[str]) -> tuple[str, ...]:
    labels = {
        "missing_city": "City / destination",
        "missing_hotel_name": "Hotel name",
        "missing_hotel_nights": "Hotel nights",
        "missing_room_category": "Room category",
        "missing_route_origin": "Route origin",
        "missing_route_destination": "Route destination",
        "missing_activity_title": "Activity title",
    }
    return tuple(labels[flag] for flag in flags if flag in labels)


def _destination_status(city: str) -> str:
    text = str(city or "").strip()
    if not text or text == "Not detected":
        return "Not detected"
    if destination_for_alias(text) is not None:
        return "Known destination"
    return "Confirm destination"


def _confidence_label(confidence: int) -> str:
    if confidence < 70:
        return "Low"
    if confidence < 90:
        return "Medium"
    return "High"


def _suggested_fixes(row: Mapping[str, Any], flags: tuple[str, ...], destination_status: str = "") -> tuple[str, ...]:
    fixes: list[str] = []
    service_type = get_row_type(row) or "Other"
    declared_type = _text(row, "type")
    effective_type = _text(row, "effective_type")
    if declared_type and effective_type and declared_type != effective_type:
        fixes.append(f"Review row type correction: {declared_type} → {effective_type}.")
    if "missing_city" in flags:
        fixes.append("Confirm the destination before generation.")
    if destination_status == "Confirm destination":
        fixes.append("Confirm destination spelling or add it to the registry.")
    if "missing_hotel_name" in flags:
        fixes.append("Add the hotel name or mark the row as accommodation TBD.")
    if "missing_hotel_nights" in flags:
        fixes.append("Add the number of nights/check-out logic.")
    if "missing_route_origin" in flags or "missing_route_destination" in flags:
        fixes.append("Confirm from/to points for this transport row.")
    if "missing_activity_title" in flags or "weak_title" in flags:
        fixes.append("Give this activity a clear client-facing title.")
    if "very_long_supplier_text" in flags:
        fixes.append("Review long supplier prose for leaked booking/admin text.")
    if not fixes and _confidence(row) < 90:
        fixes.append(f"Review parsed {service_type.lower()} fields before polishing.")

    seen: set[str] = set()
    unique: list[str] = []
    for fix in fixes:
        if fix not in seen:
            seen.add(fix)
            unique.append(fix)
    return tuple(unique)


def _primary_fix(fixes: tuple[str, ...]) -> str:
    return fixes[0] if fixes else "No action needed"


def _review_priority(status: str, confidence: int) -> str:
    if status == "Check before generation":
        return "Blocker"
    if status == "Needs review" or confidence < 90:
        return "Review"
    return "Ready"


def _next_action(row: Mapping[str, Any], status: str, fixes: tuple[str, ...], destination_status: str) -> str:
    declared_type = _text(row, "type")
    effective_type = _text(row, "effective_type")
    if declared_type and effective_type and declared_type != effective_type:
        return f"Accept type: {effective_type}"
    if destination_status == "Confirm destination":
        return "Confirm destination"
    if status == "Check before generation":
        return "Fill required field"
    if fixes:
        return "Review suggestion"
    return "No action"


def _status(confidence: int, flags: tuple[str, ...], destination_status: str = "") -> str:
    critical_flags = {
        "missing_hotel_name",
        "missing_route_destination",
        "missing_activity_title",
    }
    if confidence < 70 or any(flag in critical_flags for flag in flags):
        return "Check before generation"
    if confidence < 90 or flags or destination_status == "Confirm destination":
        return "Needs review"
    return "Ready"


def _row_title(row: Mapping[str, Any]) -> str:
    return _text(row, "title", "original_title", "hotel_name", "name") or "Untitled row"


def build_input_row_reviews(rows: Iterable[Mapping[str, Any]] | None) -> tuple[StructuredInputRowReview, ...]:
    """Return row-level supplier input review records for an import table."""

    reviews: list[StructuredInputRowReview] = []
    for index, row in enumerate(_rows(rows), start=1):
        flags = tuple(str(flag) for flag in (row.get("parser_review_flags") or []) if str(flag or "").strip())
        confidence = _confidence(row)
        city = _text(row, "city", "destination", "route_destination", "to") or "Not detected"
        destination_status = _destination_status(city)
        fixes = _suggested_fixes(row, flags, destination_status)
        status = _status(confidence, flags, destination_status)
        reviews.append(
            StructuredInputRowReview(
                row_number=index,
                day=_text(row, "day") or "Unassigned",
                service_type=get_row_type(row) or "Other",
                city=city,
                title=_row_title(row),
                confidence=confidence,
                confidence_label=_confidence_label(confidence),
                status=status,
                review_priority=_review_priority(status, confidence),
                destination_status=destination_status,
                primary_fix=_primary_fix(fixes),
                next_action=_next_action(row, status, fixes, destination_status),
                flags=flags,
                missing_fields=_missing_fields(flags),
                suggested_fixes=fixes,
            )
        )
    return tuple(reviews)
