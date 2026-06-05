"""Build UI-neutral render documents from the structured itinerary model.

This module is the consolidation layer between normalized supplier rows and the
HTML/PDF renderers.  It keeps ``ItineraryDocument`` as the owner of source-row
identity, day order and model warnings, while preserving the current row-backed
render block builders until every block type has been fully typed.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Mapping, Sequence

from itinerary_generation.common import group_rows_by_day, is_optional_row
from itinerary_generation.render_model import RenderDocument
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.structured_model import ItineraryDocument
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title


def _row_id(row: Mapping[str, object], fallback_index: int = 0) -> str:
    value = str(row.get("row_id") or "").strip()
    return value or f"generated-row-{fallback_index}"


def rows_by_source_id(rows: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    """Return a stable source-row lookup keyed like ``SourceRowRef.row_id``."""

    return {_row_id(row, index): row for index, row in enumerate(rows or [])}


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
