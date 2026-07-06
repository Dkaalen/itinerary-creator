"""Small presentation helpers for the Streamlit project header."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from itinerary_generation.common import get_row_type, group_rows_by_day, is_optional_row


TRAVEL_ROW_TYPES = {"Transfer", "Flight", "Train", "Ferry", "Cruise", "Rental Car"}


def _unique_destinations(parsed_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    destinations: list[str] = []
    for row in parsed_rows:
        city = str(row.get("city", "")).strip()
        if city and city not in destinations:
            destinations.append(city)
    return destinations


def build_project_metrics(parsed_rows: Sequence[Mapping[str, Any]], output_edits: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return compact project metrics used by the normal app header."""

    parsed_rows = list(parsed_rows or [])
    grouped_days = group_rows_by_day(parsed_rows) if parsed_rows else {}
    destinations = _unique_destinations(parsed_rows)
    billable_rows = [row for row in parsed_rows if not is_optional_row(row)]

    return {
        "days": len(grouped_days),
        "destinations": len(destinations),
        "destination_names": destinations,
        "activities": sum(1 for row in billable_rows if get_row_type(row) == "Activity"),
        "hotels": sum(1 for row in billable_rows if get_row_type(row) == "Hotel"),
        "transfers": sum(1 for row in billable_rows if get_row_type(row) in TRAVEL_ROW_TYPES),
        "optional_rows": sum(1 for row in parsed_rows if is_optional_row(row)),
        "pictures_added": bool((output_edits or {}).get("pictures_added")),
    }


def project_title(output_edits: Mapping[str, Any] | None, default: str = "New itinerary") -> str:
    value = str((output_edits or {}).get("trip_title", "")).strip()
    return value or default


def project_route_label(metrics: Mapping[str, Any]) -> str:
    destinations = list(metrics.get("destination_names", []) or [])
    if not destinations:
        return "No route detected yet"
    if len(destinations) <= 3:
        return " → ".join(destinations)
    return f"{destinations[0]} → {destinations[1]} → {destinations[2]} + {len(destinations) - 3} more"


def project_next_action_label(stage: str, metrics: Mapping[str, Any]) -> str:
    """Return compact next-step copy for the workspace shell."""

    normalized = str(stage or "input")
    pictures_added = bool(metrics.get("pictures_added"))
    if normalized == "edit":
        return "Next · apply changes"
    if normalized == "pictures":
        return "Next · review images" if pictures_added else "Next · add pictures"
    if normalized == "export":
        return "Next · create PDF"
    return "Next · paste text"
