"""Structured-document item builders."""

from __future__ import annotations

from itinerary_generation.common import get_row_type
from itinerary_generation.group_tour_rendering import group_tour_day_city, group_tour_day_title, group_tour_package_from_rows
from itinerary_generation.structured_model import DocumentItem, DocumentItemKind
from itinerary_generation.structured_row_helpers import _clean, _row_id, _source_ref, _source_text
from itinerary_generation.structured_warning_builder import _ambiguous_row_warnings, _row_data_warnings

_TRANSPORT_KIND_BY_TYPE = {
    "Transfer": "transfer",
    "Transport": "transfer",
    "Train": "rail",
    "Flight": "flight",
    "Ferry": "ferry",
    "Cruise": "cruise",
    "Drive": "transfer",
}

def _kind_for_row(row: dict) -> DocumentItemKind:
    if row.get("group_tour_role") in {"package_master", "day_segment"}:
        return "activity"
    row_type = str(get_row_type(row) or "").strip()
    if row_type == "Hotel":
        return "accommodation"
    if row_type == "Activity":
        return "activity"
    if row_type in _TRANSPORT_KIND_BY_TYPE:
        return _TRANSPORT_KIND_BY_TYPE[row_type]  # type: ignore[return-value]
    if row_type == "Leisure":
        return "leisure"
    if row_type == "Arrival":
        return "arrival"
    if row_type == "Departure":
        return "departure"
    if row_type == "Notes":
        return "note"
    text = _source_text(row).lower()
    if any(marker in text for marker in ("rental car", "rental vehicle", "car rental")):
        return "rental_vehicle"
    return "unknown"


def _item_title(row: dict) -> str:
    if row.get("group_tour_role") == "package_master":
        package = group_tour_package_from_rows([row])
        if package is not None:
            return package.title
    if row.get("group_tour_role") == "day_segment":
        title = group_tour_day_title([row])
        if title:
            return title
    for key in ("title", "hotel_name", "original_title", "details"):
        text = _clean(row.get(key, ""))
        if text:
            return text[:180].strip(" -:|")
    return "Untitled item"


def _detail_lines(row: dict) -> tuple[str, ...]:
    lines: list[str] = []
    for key in ("time", "duration", "meeting_point", "end_point", "room_category", "meal_plan", "luggage_included"):
        value = _clean(row.get(key, ""))
        if value:
            label = key.replace("_", " ").title()
            lines.append(f"{label}: {value}")
    includes = row.get("includes") or []
    if isinstance(includes, list):
        lines.extend(_clean(item) for item in includes if _clean(item))
    return tuple(lines)

def _document_item(row: dict, fallback_index: int) -> DocumentItem:
    row_id = _row_id(row, fallback_index)
    warnings = _ambiguous_row_warnings(row) + _row_data_warnings(row)
    confidence = 0.55 if warnings else 1.0
    destination = str(row.get("city", "") or "")
    if row.get("group_tour_role") == "day_segment":
        destination = group_tour_day_city([row])
    metadata: dict[str, object] = {}
    if row.get("activity_product") or row.get("route_legs"):
        metadata.update({
            "activity_product": row.get("activity_product") or {},
            "route_legs": row.get("route_legs") or [],
        })
    if row.get("group_tour_package"):
        metadata["group_tour_package"] = row.get("group_tour_package")
    if row.get("group_tour_day"):
        metadata["group_tour_day"] = row.get("group_tour_day")

    return DocumentItem(
        item_id=row_id,
        kind=_kind_for_row(row),
        day=str(row.get("day", "") or ""),
        date=str(row.get("start_date", "") or ""),
        destination=destination,
        title=_item_title(row),
        source_row_ids=(row_id,),
        commercial_status=str(row.get("commercial_status") or ("optional" if row.get("is_optional") else "included")),
        confidence=confidence,
        detail_lines=_detail_lines(row),
        warnings=warnings,
        metadata=metadata,
    )

__all__ = [
    "_TRANSPORT_KIND_BY_TYPE",
    "_clean",
    "_row_id",
    "_source_text",
    "_source_ref",
    "_kind_for_row",
    "_item_title",
    "_detail_lines",
    "_document_item",
]
