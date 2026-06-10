"""Build UI-neutral render blocks for itinerary day pages."""

from __future__ import annotations

import re

from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.canonical_accommodation import canonical_accommodation_block
from itinerary_generation.canonical_builder import should_hide_note_row
from itinerary_generation.canonical_day_builder import canonical_day
from itinerary_generation.common import get_primary_city, get_row_type, is_optional_row
from itinerary_generation.content_engine import clean_client_title, group_tour_pickup_window_from_overview, is_group_tour_overview
from itinerary_generation.editable_draft import day_by_id
from itinerary_generation.day_overview_blocks import build_day_overview_render_block
from itinerary_generation.day_planner import plan_day
from itinerary_generation.canonical_render_adapter import render_block_from_canonical
from itinerary_generation.render_model import RenderBlock, RenderDay, RenderMetaLine
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.structured_model import DayDocument, ItineraryDocument, TravelSequence
from shared.source_rows import source_row_id, rows_by_source_id
from itinerary_generation.render_text_helpers import normalize_list
from itinerary_generation.time_display import display_time_with_duration
from itinerary_generation.title_safety import is_forbidden_client_title
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.transport_render_blocks import is_cruise_leisure_row
from itinerary_generation.travel_sequence_blocks import build_travel_arrangements_render_block, is_travel_sequence_candidate
from text_polish import polish_client_text, polish_inclusion_items, polish_title, strip_price_fragments


def _group_tour_start_time(rows):
    for row in rows:
        pickup = group_tour_pickup_window_from_overview(row)
        if pickup:
            return pickup
    return ""


def _is_group_tour_overview_row(row):
    return is_group_tour_overview(row)


def _is_blank_activity_row(row):
    if get_row_type(row) != "Activity":
        return False
    raw = " ".join(str(row.get(key, "") or "").strip() for key in ["title", "details", "original_title"] if str(row.get(key, "") or "").strip())
    raw = " ".join(raw.split()).strip()
    city = " ".join(str(row.get("city", "") or "").split()).strip()
    if not raw:
        return True
    lower = raw.lower().strip(" -:|")
    if city and lower == city.lower():
        return True

    def _matches_leisure(value):
        item = " ".join(str(value or "").split()).lower().strip(" -:|")
        if not item:
            return False
        pattern = r"spend time at leisure\.?"
        if city:
            pattern = rf"(?:{re.escape(city.lower())}:?\s*)?{pattern}"
        return bool(re.fullmatch(pattern, item) or (city and re.fullmatch(rf"a day at leisure in {re.escape(city.lower())}\.?", item)))

    if any(_matches_leisure(row.get(key, "")) for key in ["title", "original_title", "details"]):
        return True
    leisure_pattern = r"spend time at leisure\.?"
    if city:
        leisure_pattern = rf"(?:{re.escape(city.lower())}:?\s*)?{leisure_pattern}"
    if re.fullmatch(leisure_pattern, lower):
        return True
    return bool(city and re.fullmatch(rf"a day at leisure in {re.escape(city.lower())}\.?", lower))


def build_leisure_render_block(row=None):
    return RenderBlock(
        kind="leisure",
        row_id=str((row or {}).get("row_id") or ""),
        section_title="Your Free Time",
        description=(
            "Enjoy the remaining time at your own pace, whether you prefer a relaxed meal, "
            "a quiet walk nearby or simply settling into the destination."
        ),
        css_class="leisure-block",
    )


def build_cruise_leisure_render_block(row):
    return RenderBlock(
        kind="cruise_leisure",
        row_id=str(row.get("row_id") or ""),
        section_title="Onboard leisure",
        title="Spend time at leisure onboard the cruise",
        description=(
            "Enjoy a relaxed day onboard the cruise, with time to take in the coastal scenery, "
            "use the ship facilities and settle into the rhythm of the voyage."
        ),
        css_class="cruise-leisure-block",
    )


def build_arrival_render_block(row):
    city = polish_title(row.get("city", ""))
    title = clean_client_title(row.get("title", ""), row)
    if is_forbidden_client_title(title) or not title or title.lower().strip(" .") in {"arrival", "arrival day", "welcome", "welcome day"}:
        title = f"Arrival in {city}" if city else "Arrival"
    return RenderBlock(
        kind="arrival",
        row_id=str(row.get("row_id") or ""),
        section_title="Arrival",
        title=title,
        css_class="arrival-block",
    )


def build_departure_render_block(row):
    title = clean_client_title(row.get("title", "") or "", row)
    if is_forbidden_client_title(title) or not title or title.lower().strip(" .") in {"departure", "departure day"}:
        title = "Journey home"
    return RenderBlock(
        kind="departure",
        row_id=str(row.get("row_id") or ""),
        section_title="Departure",
        title=title,
        css_class="departure-block",
    )


def build_included_today_render_block(items):
    clean_items = polish_inclusion_items(normalize_list(items))
    if not clean_items:
        return None
    return RenderBlock(
        kind="included",
        row_id="included-today",
        section_title="Included Today",
        lines=clean_items,
        css_class="included-block",
    )


def _optional_title(row: dict) -> str:
    title = create_client_activity_title(row) if (row.get("effective_type") or row.get("type")) == "Activity" else row.get("title", "")
    title = normalize_client_day_title(title or row.get("title") or "Optional experience", row)
    return polish_title(strip_price_fragments(title)) or "Optional experience"


def build_optional_render_block(row: dict) -> RenderBlock:
    row_id = str(row.get("row_id") or "")
    row_type = row.get("effective_type") or row.get("type", "")
    title = _optional_title(row)
    meta: list[RenderMetaLine] = []
    time_display = row.get("display_time") or display_time_with_duration(row.get("time", ""), row.get("duration", ""))
    if time_display:
        meta.append(RenderMetaLine("Time", time_display))

    description = ""
    if row_type == "Activity":
        block = canonical_activity_block(dict(row, display_title=title))
        description = block.description
        for item in block.meta:
            if item.label in {"Meeting point", "Pick-up/drop-off", "Departure/drop-off"} and item.value:
                meta.append(RenderMetaLine(item.label or "Meeting point", strip_price_fragments(item.value)))
                break
    if not description:
        description = polish_client_text(row.get("description", "") or row.get("details", ""))

    return RenderBlock(
        kind="optional_experience",
        row_id=row_id,
        section_title="Optional Experience",
        title=title,
        meta=meta,
        description=description,
        css_class="optional-experience-block",
    )


def build_day_render_blocks(rows, travel_sequences: list[TravelSequence] | tuple[TravelSequence, ...] | None = None):
    """Build day blocks in source order as UI-neutral render blocks.

    When available, TravelSequence objects from the structured document own the
    travel grouping.  The renderer then only places the precomputed sequence at
    the first source row instead of discovering consecutive transport rows late.
    """

    blocks: list[RenderBlock] = []
    travel_group: list[dict] = []
    sequence_by_first_row = {str(sequence.source_row_ids[0]): sequence for sequence in (travel_sequences or []) if sequence.source_row_ids}
    sequence_row_ids = {str(row_id) for sequence in (travel_sequences or []) for row_id in sequence.source_row_ids}
    row_lookup = rows_by_source_id(rows)
    main_rows = [row for row in rows if not is_optional_row(row)] or list(rows)
    day_plan = plan_day(main_rows)
    departure_day = any(get_row_type(row) == "Departure" for row in main_rows)
    has_activity = any(get_row_type(row) == "Activity" and not _is_blank_activity_row(row) for row in main_rows)
    group_tour_start_time = _group_tour_start_time(main_rows)

    def flush_travel_group():
        nonlocal travel_group
        if travel_group:
            block = build_travel_arrangements_render_block(travel_group)
            if block:
                blocks.append(block)
            travel_group = []

    for source_row in rows:
        row = source_row
        row_type = get_row_type(row)
        title = row.get("title", "")

        if is_optional_row(row):
            flush_travel_group()
            blocks.append(build_optional_render_block(row))
            continue

        current_row_id = _row_id(row)
        if current_row_id in sequence_by_first_row:
            flush_travel_group()
            sequence = sequence_by_first_row[current_row_id]
            sequence_rows = [row_lookup[row_id] for row_id in sequence.source_row_ids if row_id in row_lookup]
            block = build_travel_arrangements_render_block(sequence_rows)
            if block:
                block.row_id = sequence.sequence_id
                block.source_row_ids = list(sequence.source_row_ids)
                block.warnings.extend(
                    warning for warning in [
                        "Travel sequence has no final destination; review source route endpoints." if not sequence.final_destination else "",
                    ] if warning
                )
                blocks.append(block)
            continue
        if current_row_id in sequence_row_ids:
            continue

        if is_travel_sequence_candidate(row):
            if departure_day and row_type == "Transfer" and "to your accommodation" in str(row.get("title", "")).lower():
                row = dict(row)
                city = get_primary_city(rows) or row.get("city", "")
                row["title"] = f"Private transfer from your hotel to {polish_title(city)} Airport" if city else "Private transfer from your hotel to the airport"
            travel_group.append(row)
            continue

        flush_travel_group()

        if row_type == "Departure":
            generic_departure = re.search(r"^(departure|departure\s+day|departure\s+home|journey\s+home)$", str(row.get("title", "")).strip(), flags=re.IGNORECASE)
            if not generic_departure:
                blocks.append(build_departure_render_block(row))
        elif row_type == "Day Overview":
            if has_activity and _is_group_tour_overview_row(row):
                continue
            block = build_day_overview_render_block(row)
            if block:
                blocks.append(block)
        elif row_type == "Car":
            block = build_day_overview_render_block(row)
            if block:
                blocks.append(block)
        elif row_type == "Hotel":
            blocks.append(render_block_from_canonical(canonical_accommodation_block(row)))
        elif row_type == "Arrival":
            generic_arrival = re.search(r"^(arrival|welcome\s+to\s+.+)$", str(row.get("title", "")).strip(), flags=re.IGNORECASE)
            if not generic_arrival:
                blocks.append(build_arrival_render_block(row))
        elif row_type == "Activity":
            if _is_blank_activity_row(row):
                continue
            if group_tour_start_time and not row.get("time"):
                row = dict(row)
                row["group_tour_pickup_range"] = group_tour_start_time
            blocks.append(render_block_from_canonical(canonical_activity_block(row)))
        elif row_type == "Leisure":
            if day_plan.suppress_free_time or (travel_group and len(rows) > 3):
                continue
            blocks.append(build_leisure_render_block(row))
        elif row_type in {"Notes", "Note"}:
            if should_hide_note_row(row):
                continue
            continue
        elif is_cruise_leisure_row(row):
            blocks.append(build_cruise_leisure_render_block(row))
        elif title:
            included_block = build_included_today_render_block([polish_title(title)])
            if included_block:
                blocks.append(included_block)

    flush_travel_group()
    return blocks


def _row_id(row: dict, fallback_index: int = 0) -> str:
    return source_row_id(row, fallback_index)


def _day_document_for(document: ItineraryDocument, day: str) -> DayDocument | None:
    for day_document in document.days:
        if str(day_document.day) == str(day):
            return day_document
    return None


def _rows_ordered_by_day_document(day_document: DayDocument | None, rows: list[dict]) -> list[dict]:
    """Return day rows in the structured document's source order.

    Optional rows may be appended only for day-page rendering and therefore may
    not be present in the main DayDocument.  They are preserved at the end in
    their incoming order so the render document can remain source-aware without
    dropping explicit optional experiences.
    """

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
    """Return edits where typed editor day fields directly own PDF titles.

    ``editor_draft`` is the preferred save contract.  The legacy
    ``output_edits["days"]`` mirror is kept for compatibility, but render/PDF
    ownership should not depend on that mirror being populated.
    """

    if not isinstance(output_edits, dict):
        return output_edits
    editor_draft = output_edits.get("editor_draft") if isinstance(output_edits.get("editor_draft"), dict) else {}
    typed_day = day_by_id(editor_draft, day) if isinstance(editor_draft, dict) else {}
    if not typed_day:
        return output_edits
    direct_fields = {
        field: str(typed_day.get(field, "")).strip()
        for field in ("title", "city", "intro")
        if field in typed_day and str(typed_day.get(field, "")).strip()
    }
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
) -> RenderDay:
    """Build one RenderDay from the structured itinerary source document."""

    ordered_rows = _rows_ordered_by_day_document(_day_document_for(document, day), rows)
    main_rows = [row for row in ordered_rows if not is_optional_row(row)] or list(ordered_rows)
    effective_output_edits = _output_edits_with_typed_day_overrides(output_edits, day)
    day_shell = canonical_day(day, main_rows, output_edits=effective_output_edits, detail_level=detail_level)
    day_document = _day_document_for(document, day)
    source_ids = list(day_document.source_row_ids) if day_document else list(day_shell.source_row_ids)
    warnings = list(day_shell.warnings)
    if day_document:
        warnings.extend(warning.message for warning in day_document.warnings)
    return RenderDay(
        day=day_shell.day,
        number=day_document.number if day_document and day_document.number else day_shell.number,
        city=day_shell.city,
        title=day_shell.title,
        intro=day_shell.intro,
        date=day_document.date if day_document and day_document.date else "",
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
