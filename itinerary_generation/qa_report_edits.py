"""Collect edit events for the persistent QA report."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from itinerary_generation.common import get_primary_city, get_row_type, group_rows_by_day
from itinerary_generation.day_text import create_day_intro, create_travel_route_label
from itinerary_generation.qa_report_helpers import (
    _block_text,
    _clean,
    _event_action,
    _product_family,
    _row_generated_value,
    _row_id,
    _source_text,
)
from itinerary_generation.qa_report_model import QaEditEvent
from itinerary_generation.titles import create_day_title


def _day_source_text(day_rows: list[Mapping[str, Any]]) -> str:
    snippets = [_source_text(row) for row in day_rows[:3] if _source_text(row)]
    return _block_text(" | ".join(snippets))


def _collect_day_edit_events(
    grouped: Mapping[str, list[dict[str, Any]]],
    day_edits: Mapping[str, Any],
    output_edits: Mapping[str, Any],
) -> list[QaEditEvent]:
    events: list[QaEditEvent] = []
    for day, day_rows in grouped.items():
        edits = day_edits.get(day, {}) if isinstance(day_edits.get(day), Mapping) else {}
        if not edits:
            continue
        generated = {
            "title": create_day_title(day_rows),
            "city": create_travel_route_label(day_rows) or get_primary_city(day_rows),
            "intro": create_day_intro(day_rows, detail_level=output_edits.get("detail_level", "Rich descriptive")),
        }
        for field_name, original in generated.items():
            if field_name not in edits:
                continue
            edited = str(edits.get(field_name, ""))
            if _clean(edited) == _clean(original):
                continue
            city = str(edits.get("city") or generated.get("city") or get_primary_city(day_rows))
            events.append(QaEditEvent(
                event_type="day_edit",
                location=f"{day} · {city} · Day {field_name}",
                day=day,
                city=city,
                section="Day header" if field_name in {"title", "city"} else "Day intro",
                field=field_name,
                original_text=_block_text(original),
                edited_text=_block_text(edited),
                source_text=_day_source_text(day_rows),
                suggested_action=_event_action(field_name),
            ))
        if "blocks_html" in edits:
            city = str(edits.get("city") or get_primary_city(day_rows))
            events.append(QaEditEvent(
                event_type="visual_day_block_edit",
                location=f"{day} · {city} · Visual page content",
                day=day,
                city=city,
                section="Visual page content",
                field="blocks_html",
                original_text="Generated day content block",
                edited_text=_block_text(edits.get("blocks_html", "")),
                source_text=_day_source_text(day_rows),
                suggested_action=_event_action("blocks_html"),
            ))
    return events


def _collect_row_edit_events(rows: list[dict[str, Any]], row_edits: Mapping[str, Any]) -> list[QaEditEvent]:
    events: list[QaEditEvent] = []
    editable_fields = (
        "title", "city", "time", "duration", "client_description", "meeting_point",
        "end_point", "luggage_included", "hotel_name", "hotel_nights", "room_category",
        "meal_plan", "notable_sights_text", "includes_text",
    )
    for row in rows:
        row_id = _row_id(row)
        edits = row_edits.get(row_id, {}) if isinstance(row_edits.get(row_id), Mapping) else {}
        if not edits:
            continue
        row_type = get_row_type(row)
        day = str(row.get("day", "")).strip()
        city = str(edits.get("city") or row.get("city") or "").strip()
        for field_name in editable_fields:
            if field_name not in edits:
                continue
            original = _row_generated_value(row, field_name)
            edited = str(edits.get(field_name, ""))
            if _clean(edited) == _clean(original):
                continue
            events.append(QaEditEvent(
                event_type="row_edit",
                location=f"{day} · {city} · {row_type} · {field_name}",
                day=day,
                city=city,
                section=row_type,
                field=field_name,
                original_text=_block_text(original),
                edited_text=_block_text(edited),
                source_text=_source_text(row),
                source_row_id=row_id,
                product_family=_product_family(row),
                suggested_action=_event_action(field_name, row_type),
            ))
    return events


def _collect_final_page_edit_events(output_edits: Mapping[str, Any]) -> list[QaEditEvent]:
    events: list[QaEditEvent] = []
    final_fields = {
        "whats_included_text": "What's included",
        "whats_included_html": "What's included",
        "whats_included_pages_html": "What's included",
        "whats_not_included_text": "What's not included",
        "whats_not_included_html": "What's not included",
        "important_travel_notes_text": "Important travel notes",
    }
    for field_name, section in final_fields.items():
        if output_edits.get(field_name):
            events.append(QaEditEvent(
                event_type="final_page_edit",
                location=f"Final pages · {section}",
                section=section,
                field=field_name,
                original_text="Generated final-page content",
                edited_text=_block_text(output_edits.get(field_name)),
                suggested_action=_event_action("whats_included" if "included" in field_name else field_name),
            ))
    return events


def _collect_visual_issue_events(output_edits: Mapping[str, Any]) -> list[QaEditEvent]:
    events: list[QaEditEvent] = []
    flags = output_edits.get("visual_editor_issue_flags") if isinstance(output_edits.get("visual_editor_issue_flags"), list) else []
    for flag in flags:
        if not isinstance(flag, Mapping):
            continue
        events.append(QaEditEvent(
            event_type="editor_issue_flag",
            location=str(flag.get("label") or flag.get("key") or "Visual editor issue"),
            section="Visual editor",
            field=str(flag.get("key", "")),
            original_text=_block_text(flag.get("original", "")),
            edited_text=_block_text(flag.get("corrected", "")),
            suggested_action="Review the flagged visual-editor correction and add a regression test if it reflects a generator mistake.",
        ))
    return events


def collect_edit_events(parsed_rows: Iterable[Mapping[str, Any]], output_edits: Mapping[str, Any]) -> tuple[QaEditEvent, ...]:
    rows = [dict(row) for row in parsed_rows or []]
    grouped = group_rows_by_day(rows)
    day_edits = output_edits.get("days", {}) if isinstance(output_edits.get("days"), Mapping) else {}
    row_edits = output_edits.get("rows", {}) if isinstance(output_edits.get("rows"), Mapping) else {}
    events: list[QaEditEvent] = []
    events.extend(_collect_day_edit_events(grouped, day_edits, output_edits))
    events.extend(_collect_row_edit_events(rows, row_edits))
    events.extend(_collect_final_page_edit_events(output_edits))
    events.extend(_collect_visual_issue_events(output_edits))
    return tuple(events)
