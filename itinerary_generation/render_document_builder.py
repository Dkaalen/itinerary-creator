"""Build UI-neutral render documents from the structured itinerary model.

This module is the consolidation layer between normalized supplier rows and the
HTML/PDF renderers.  It keeps ``ItineraryDocument`` as the owner of source-row
identity, day order and model warnings, while preserving the current row-backed
render block builders until every block type has been fully typed.
"""

from __future__ import annotations

from collections import OrderedDict
import re
from typing import Mapping

from itinerary_generation.common import get_row_type, group_rows_by_day, is_optional_row
from itinerary_generation.copy.visit_context import build_day_visit_contexts
from itinerary_generation.render_model import RenderDocument
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.structured_model import ItineraryDocument
from shared.source_rows import source_row_id
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title
from itinerary_generation.transport_domain.route_summary import transport_destination_from_row


def _row_id(row: Mapping[str, object], fallback_index: int = 0) -> str:
    return source_row_id(row, fallback_index)



def _numeric_day(value: object) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def _next_render_day_key(rendered: OrderedDict, day_value: object) -> object | None:
    day_number = _numeric_day(day_value)
    if day_number is None:
        return None
    for key in rendered.keys():
        if _numeric_day(key) == day_number + 1:
            return key
    return None


def _synthetic_overnight_cruise_arrival_rows(parsed_rows, rendered: OrderedDict) -> list[tuple[object, dict]]:
    arrivals: list[tuple[object, dict]] = []
    for row in parsed_rows or []:
        if get_row_type(row) != "Cruise":
            continue
        source_text = " ".join(str(row.get(key) or "") for key in ("title", "original_title", "details", "raw"))
        if "overnight" not in source_text.lower():
            continue
        next_key = _next_render_day_key(rendered, row.get("day"))
        if next_key is None:
            continue
        destination = transport_destination_from_row(row)
        destination = str(destination or "").strip()
        if not destination:
            continue
        next_rows = rendered.get(next_key) or []
        if any("cruise arrival" in str(existing.get("title", "")).lower() for existing in next_rows):
            continue
        next_city = next((str(existing.get("city") or "").strip() for existing in next_rows if existing.get("city")), destination)
        if next_city and destination.lower() not in {next_city.lower(), f"{next_city.lower()} port"}:
            # Keep the arrival on the following itinerary day only when the
            # next day belongs to the cruise destination.
            continue
        arrival_destination = f"{destination} Port" if "port" not in destination.lower() else destination
        source_id = _row_id(row)
        arrivals.append((next_key, {
            "raw": f"{destination}: Cruise arrival to {arrival_destination}",
            "row_id": f"{source_id}-arrival",
            "is_render_only": True,
            "render_position": "start",
            "day": next_key,
            "type": "Cruise",
            "source_type": "Cruise",
            "effective_type": "Cruise",
            "commercial_status": "included",
            "city": destination,
            "title": f"Cruise arrival to {arrival_destination}",
            "original_title": f"Cruise arrival to {arrival_destination}",
            "details": "",
            "time": "",
            "includes": [],
        }))
    return arrivals


def grouped_days_with_day_optional_rows(grouped_days, parsed_rows):
    """Return a render-only day grouping with optional rows shown in context.

    Core grouping intentionally excludes optional rows so route, duration and
    confirmed itinerary summaries remain based on confirmed content.  Day pages
    still need to show explicit optional experiences under the matching day.
    """

    rendered = OrderedDict((day, list(rows)) for day, rows in (grouped_days or {}).items())
    for row in parsed_rows or []:
        if not is_optional_row(row):
            continue
        day = row.get("day", "")
        if day in rendered:
            rendered[day].append(row)
    for day, arrival_row in _synthetic_overnight_cruise_arrival_rows(parsed_rows, rendered):
        rendered[day].insert(0, arrival_row)
    return rendered


def build_render_document_from_document(
    document: ItineraryDocument,
    parsed_rows: list[dict],
    grouped_days: dict[str, list[dict]],
    *,
    output_edits: dict | None = None,
    detail_level: str = "Rich descriptive",
) -> RenderDocument:
    """Build a RenderDocument using an existing structured source document."""

    # Import lazily to avoid a module cycle: day block builders use RenderBlock,
    # while this builder coordinates complete RenderDocument assembly.
    from itinerary_generation.day_render_blocks import build_render_day_from_document

    render_grouped_days = grouped_days_with_day_optional_rows(grouped_days, parsed_rows)
    visit_contexts = build_day_visit_contexts(grouped_days or {})
    warnings = [warning.message for warning in document.warnings]
    return RenderDocument(
        title=create_trip_title(parsed_rows, grouped_days),
        subtitle=create_trip_subtitle(parsed_rows, grouped_days),
        route=create_destinations_line(parsed_rows),
        days=[
            build_render_day_from_document(
                document,
                day,
                list(rows),
                output_edits=output_edits,
                detail_level=detail_level,
                visit_context=visit_contexts.get(str(day)),
            )
            for day, rows in render_grouped_days.items()
        ],
        warnings=warnings,
    )


def build_render_document(
    parsed_rows: list[dict],
    grouped_days: dict[str, list[dict]] | None = None,
    *,
    output_edits: dict | None = None,
    detail_level: str = "Rich descriptive",
) -> RenderDocument:
    """Build the typed render contract from normalized rows.

    This is the preferred day-page entry point for new code.  It constructs the
    structured itinerary once, then renders days from that structured document.
    """

    grouped = OrderedDict(grouped_days or group_rows_by_day(parsed_rows or []))
    document = build_itinerary_document(parsed_rows or [], grouped)
    return build_render_document_from_document(
        document,
        parsed_rows or [],
        grouped,
        output_edits=output_edits,
        detail_level=detail_level,
    )
