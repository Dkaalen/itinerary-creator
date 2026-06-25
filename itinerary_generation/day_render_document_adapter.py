"""Structured document to render-day adapter."""

from __future__ import annotations

from itinerary_generation.canonical_day_builder import canonical_day
from itinerary_generation.common import is_optional_row
from itinerary_generation.copy.visit_context import DayVisitContext
from itinerary_generation.day_content_resolver import resolve_day_content
from itinerary_generation.day_render_block_ordering import _row_id, build_day_render_blocks
from itinerary_generation.editable_draft import day_by_id
from itinerary_generation.render_model import RenderBlock, RenderDay
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.structured_model import DayDocument, ItineraryDocument, TravelSequence
from shared.source_rows import rows_by_source_id


def _day_document_for(document: ItineraryDocument, day: str) -> DayDocument | None:
    for day_document in document.days:
        if str(day_document.day) == str(day):
            return day_document
    return None


def _rows_ordered_by_day_document(day_document: DayDocument | None, rows: list[dict]) -> list[dict]:
    """Return day rows in the structured document's source order."""

    if not day_document:
        return list(rows)
    row_lookup = rows_by_source_id(rows)
    ordered: list[dict] = []
    used_ids: set[str] = set()
    for source_id in day_document.source_row_ids:
        row = row_lookup.get(str(source_id))
        if row is not None:
            ordered.append(row)
            used_ids.add(str(source_id))
    for index, row in enumerate(rows):
        row_id = _row_id(row, index)
        if row_id not in used_ids:
            ordered.append(row)
    return ordered


def _travel_sequences_for_day(document: ItineraryDocument, day: str) -> tuple[TravelSequence, ...]:
    return tuple(sequence for sequence in getattr(document, "travel_sequences", ()) if str(sequence.day) == str(day))


def _output_edits_with_typed_day_overrides(output_edits: dict | None, day: str) -> dict | None:
    """Return edits where typed editor day fields directly own PDF titles."""

    if not isinstance(output_edits, dict):
        return output_edits
    editor_draft = output_edits.get("editor_draft") if isinstance(output_edits.get("editor_draft"), dict) else {}
    typed_day = day_by_id(editor_draft, day) if isinstance(editor_draft, dict) else {}
    if not typed_day:
        return output_edits
    direct_fields = {
        field: str(typed_day.get(field, "")).strip()
        for field in ("title", "city", "date")
        if field in typed_day and str(typed_day.get(field, "")).strip()
    }
    if typed_day.get("intro_manual_override") and str(typed_day.get("intro", "")).strip():
        direct_fields["intro"] = str(typed_day.get("intro", "")).strip()
    if not direct_fields:
        return output_edits
    merged = dict(output_edits)
    days = {key: dict(value) if isinstance(value, dict) else value for key, value in (output_edits.get("days") or {}).items()}
    day_edits = dict(days.get(day, {})) if isinstance(days.get(day, {}), dict) else {}
    day_edits.update(direct_fields)
    days[day] = day_edits
    merged["days"] = days
    return merged


def build_day_render_blocks_from_document(document: ItineraryDocument, day: str, rows: list[dict]) -> list[RenderBlock]:
    """Build day render blocks using the structured document for source order."""

    day_document = _day_document_for(document, day)
    return build_day_render_blocks(_rows_ordered_by_day_document(day_document, rows), _travel_sequences_for_day(document, day))


def build_render_day_from_document(
    document: ItineraryDocument,
    day: str,
    rows: list[dict],
    *,
    output_edits: dict | None = None,
    detail_level: str = "Rich descriptive",
    visit_context: DayVisitContext | None = None,
) -> RenderDay:
    """Build one RenderDay from the structured itinerary source document."""

    ordered_rows = _rows_ordered_by_day_document(_day_document_for(document, day), rows)
    main_rows = [row for row in ordered_rows if not is_optional_row(row)] or list(ordered_rows)
    effective_output_edits = _output_edits_with_typed_day_overrides(output_edits, day)
    day_shell = canonical_day(day, main_rows, output_edits=effective_output_edits, detail_level=detail_level, visit_context=visit_context)
    day_document = _day_document_for(document, day)
    source_ids = list(day_document.source_row_ids) if day_document else list(day_shell.source_row_ids)
    warnings = list(day_shell.warnings)
    if day_document:
        warnings.extend(warning.message for warning in day_document.warnings)
    resolved_day_content = resolve_day_content(day, main_rows, output_edits=effective_output_edits, detail_level=detail_level, visit_context=visit_context)
    edited_date = str(resolved_day_content.date or "").strip()
    return RenderDay(
        day=day_shell.day,
        number=day_document.number if day_document and day_document.number else day_shell.number,
        city=day_shell.city,
        title=day_shell.title,
        intro=day_shell.intro,
        date=edited_date or (day_document.date if day_document and day_document.date else ""),
        blocks=build_day_render_blocks(ordered_rows, _travel_sequences_for_day(document, day)),
        source_row_ids=source_ids,
        warnings=list(dict.fromkeys(warnings)),
    )


def build_render_day(
    day: str,
    rows: list[dict],
    *,
    output_edits: dict | None = None,
    detail_level: str = "Rich descriptive",
    structured_document: ItineraryDocument | None = None,
) -> RenderDay:
    """Compatibility wrapper that now renders through ItineraryDocument."""

    document = structured_document or build_itinerary_document(list(rows), {day: [row for row in rows if not is_optional_row(row)] or list(rows)})
    return build_render_day_from_document(
        document,
        day,
        list(rows),
        output_edits=output_edits,
        detail_level=detail_level,
    )


__all__ = [
    "_day_document_for",
    "_output_edits_with_typed_day_overrides",
    "_row_id",
    "_rows_ordered_by_day_document",
    "_travel_sequences_for_day",
    "build_day_render_blocks_from_document",
    "build_render_day",
    "build_render_day_from_document",
]
