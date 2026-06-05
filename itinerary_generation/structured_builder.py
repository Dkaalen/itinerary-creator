"""Build the structured itinerary document from normalized rows.

This is the first migration layer away from late-stage string/HTML fixes.  The
existing preview/PDF pipeline can still render as before, but new tests and new
features should target this document model first.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Iterable

from itinerary_generation.common import get_primary_city, get_row_type, group_rows_by_day
from itinerary_generation.date_formatting import format_client_date
from itinerary_generation.exclusion_sections import create_structured_whats_not_included
from itinerary_generation.structured_inclusions import build_structured_inclusion_sections
from itinerary_generation.structured_model import (
    DayDocument,
    DocumentItem,
    DocumentItemKind,
    ItineraryDocument,
    ModelWarning,
    SourceRowRef,
    StructuredListItem,
    StructuredListSection,
)
from itinerary_generation.structured_rendering import normalize_structured_list_sections
from itinerary_generation.structured_validation import validate_itinerary_document

_TRANSPORT_KIND_BY_TYPE = {
    "Transfer": "transfer",
    "Transport": "transfer",
    "Train": "rail",
    "Flight": "flight",
    "Ferry": "ferry",
    "Cruise": "cruise",
    "Drive": "transfer",
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r\n", "\n").replace("\r", "\n").split())


def _row_id(row: dict, fallback_index: int = 0) -> str:
    value = str(row.get("row_id") or "").strip()
    if value:
        return value
    return f"generated-row-{fallback_index}"


def _source_text(row: dict) -> str:
    return "\n".join(
        str(row.get(key, "") or "")
        for key in ("raw", "original_title", "title", "details")
        if str(row.get(key, "") or "").strip()
    )


def _source_ref(row: dict, fallback_index: int) -> SourceRowRef:
    return SourceRowRef(
        row_id=_row_id(row, fallback_index),
        line_number=row.get("line_number") if isinstance(row.get("line_number"), int) else None,
        day=str(row.get("day", "") or ""),
        source_type=str(row.get("source_type") or row.get("type") or ""),
        effective_type=str(get_row_type(row) or ""),
        start_date=str(row.get("start_date", "") or ""),
        end_date=str(row.get("end_date", "") or ""),
        city=str(row.get("city", "") or ""),
        raw_text=str(row.get("raw") or row.get("details") or row.get("title") or ""),
        title=str(row.get("title", "") or ""),
        original_title=str(row.get("original_title", "") or ""),
        commercial_status=str(row.get("commercial_status") or ("optional" if row.get("is_optional") else "included")),
        commercial_reason=str(row.get("commercial_reason", "") or ""),
    )


def _kind_for_row(row: dict) -> DocumentItemKind:
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


_ACTIVITY_SIGNAL_GROUPS: tuple[tuple[str, ...], ...] = (
    ("fjord", "fjords", "fjorden", "fjordsafari", "fjord safari"),
    ("cruise", "boat", "sailing", "ferry"),
    # Generic words like "ticket" or "admission" are not specific enough to
    # imply a museum/gallery product. Keeping this signal narrow avoids false
    # warnings for rows such as generic cable-car round-trip tickets.
    ("museum", "gallery"),
    ("walking", "walk", "guided walk", "city center", "city centre"),
    ("northern lights", "aurora", "auroras"),
    ("husky", "reindeer", "safari"),
    ("cable car", "fjellheisen", "funicular", "funicual"),
    ("munch", "munch museum"),
)

_STOP_TOKENS = {
    "activity", "experience", "tour", "guided", "ticket", "tickets", "included",
    "with", "from", "into", "your", "the", "and", "for", "day", "time",
    "tromso", "tromsø", "oslo", "bergen", "helsinki", "rovaniemi", "tallinn",
}


def _signature_tokens(value: str) -> set[str]:
    tokens = {token.lower() for token in re.findall(r"[A-Za-zÀ-ÿøØåÅäÄöÖæÆðÐþÞ]{4,}", value or "")}
    return {token for token in tokens if token not in _STOP_TOKENS}


def _source_signal_warnings(title: str, source: str, row_id: str) -> list[ModelWarning]:
    """Return warnings when a cleaned activity title loses source-specific signals.

    This is a diagnostic guardrail, not a hard blocker.  It catches the class of
    bugs where one activity title/detail is accidentally overwritten by another
    row later in the pipeline, such as a museum title replacing a fjord cruise.
    """

    title_lower = title.lower()
    source_lower = source.lower()
    if not title_lower or not source_lower:
        return []

    warnings: list[ModelWarning] = []
    source_tokens = _signature_tokens(source_lower)
    title_tokens = _signature_tokens(title_lower)
    # If both sides have meaningful tokens but none overlap, the title may be
    # an inference or a cross-row contamination. Do not warn on very thin source
    # rows because those often only contain time/booking metadata.
    if len(source_tokens) >= 2 and len(title_tokens) >= 2 and source_tokens.isdisjoint(title_tokens):
        warnings.append(ModelWarning(
            code="activity_title_not_supported_by_source",
            message="Activity title has little overlap with its source row; review for possible cross-row title contamination.",
            source_row_ids=(row_id,),
        ))

    for signal_group in _ACTIVITY_SIGNAL_GROUPS:
        source_has_signal = any(signal in source_lower for signal in signal_group)
        title_has_signal = any(signal in title_lower for signal in signal_group)
        if source_has_signal and not title_has_signal:
            signal_label = signal_group[0].replace("_", " ")
            warnings.append(ModelWarning(
                code="activity_source_signal_missing_from_title",
                message=f"Activity source row mentions {signal_label}, but the display title does not; review before final output.",
                source_row_ids=(row_id,),
            ))
            break

    return warnings


def _ambiguous_row_warnings(row: dict) -> tuple[ModelWarning, ...]:
    """Flag rows where the model should not over-trust an inferred title."""

    row_type = str(get_row_type(row) or "")
    if row_type != "Activity":
        return ()

    # Use only supplier/source fields for ambiguity checks. The normalized
    # title may already contain an inferred product name, which would otherwise
    # make the inference look falsely explicit.
    source = "\n".join(
        str(row.get(key, "") or "")
        for key in ("raw", "original_title", "details")
        if str(row.get(key, "") or "").strip()
    )
    source_lower = source.lower()
    title = str(row.get("title", "") or "")
    title_lower = title.lower()
    row_id = _row_id(row)

    warnings: list[ModelWarning] = []
    if "round trip ticket" in source_lower and "fjellheisen" in title_lower:
        explicit_markers = ("fjellheisen", "cable car", "funicular", "funicual")
        if not any(marker in source_lower for marker in explicit_markers):
            warnings.append(ModelWarning(
                code="ambiguous_activity_title",
                message=(
                    "Activity title was inferred from a generic 'Round Trip Ticket' row; "
                    "confirm the product name before final output."
                ),
                source_row_ids=(row_id,),
            ))

    warnings.extend(_source_signal_warnings(title, source, row_id))

    return tuple(dict.fromkeys(warnings))


def _document_item(row: dict, fallback_index: int) -> DocumentItem:
    row_id = _row_id(row, fallback_index)
    warnings = _ambiguous_row_warnings(row)
    confidence = 0.55 if warnings else 1.0
    return DocumentItem(
        item_id=row_id,
        kind=_kind_for_row(row),
        day=str(row.get("day", "") or ""),
        date=str(row.get("start_date", "") or ""),
        destination=str(row.get("city", "") or ""),
        title=_item_title(row),
        source_row_ids=(row_id,),
        commercial_status=str(row.get("commercial_status") or ("optional" if row.get("is_optional") else "included")),
        confidence=confidence,
        detail_lines=_detail_lines(row),
        warnings=warnings,
    )


def _day_number(day: str) -> str:
    match = re.search(r"\d+", str(day or ""))
    return match.group(0) if match else str(day or "").strip()


def _build_days(
    grouped_days: dict[str, list[dict]],
    item_ids_by_row_id: dict[str, str],
    row_ids_by_object: dict[int, str],
) -> tuple[DayDocument, ...]:
    days: list[DayDocument] = []
    for day, rows in grouped_days.items():
        source_ids = tuple(row_ids_by_object.get(id(row), _row_id(row, index)) for index, row in enumerate(rows))
        item_ids = tuple(item_ids_by_row_id[row_id] for row_id in source_ids if row_id in item_ids_by_row_id)
        date = ""
        for row in rows:
            if row.get("start_date"):
                date = format_client_date(row.get("start_date"))
                break
        days.append(DayDocument(
            day=str(day),
            number=_day_number(str(day)),
            date=date,
            destination=get_primary_city(rows),
            item_ids=item_ids,
            source_row_ids=source_ids,
        ))
    return tuple(days)


def _split_structured_item(value: str, category: str = "") -> StructuredListItem:
    lines = [line.strip() for line in str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    if not lines:
        return StructuredListItem(label="", category=category)
    return StructuredListItem(label=lines[0], detail_lines=tuple(lines[1:]), category=category)


def _section_from_mapping(section_id: str, title: str, raw_items: Iterable[str]) -> StructuredListSection | None:
    items = tuple(item for item in (_split_structured_item(value, section_id) for value in raw_items) if item.label)
    if not title or not items:
        return None
    return StructuredListSection(section_id=section_id, title=title, items=items)


def _inclusion_sections(parsed_rows: list[dict], grouped_days: dict[str, list[dict]]) -> tuple[StructuredListSection, ...]:
    return build_structured_inclusion_sections(parsed_rows, grouped_days)


def _exclusion_sections(parsed_rows: list[dict]) -> tuple[StructuredListSection, ...]:
    # Preserve source_row_ids and detail lines from the structured exclusion API.
    # The older string-only adapter is intentionally bypassed here so model
    # validation can audit that self-arranged/optional/excluded rows still have
    # visible What's-not-included coverage.
    return normalize_structured_list_sections(create_structured_whats_not_included(parsed_rows))


def build_itinerary_document(parsed_rows: list[dict], grouped_days: dict[str, list[dict]] | None = None) -> ItineraryDocument:
    """Build a structured document without changing the existing render path."""

    rows = list(parsed_rows or [])
    grouped = OrderedDict(grouped_days or group_rows_by_day(rows))

    row_ids_by_object = {id(row): _row_id(row, index) for index, row in enumerate(rows)}
    source_rows = tuple(_source_ref(row, index) for index, row in enumerate(rows))
    items = tuple(_document_item(row, index) for index, row in enumerate(rows))
    item_ids_by_row_id = {item.source_row_ids[0]: item.item_id for item in items if item.source_row_ids}
    days = _build_days(grouped, item_ids_by_row_id, row_ids_by_object)

    item_warnings: list[ModelWarning] = []
    for item in items:
        item_warnings.extend(item.warnings)

    document = ItineraryDocument(
        source_rows=source_rows,
        days=days,
        items=items,
        inclusions=_inclusion_sections(rows, grouped),
        exclusions=_exclusion_sections(rows),
        warnings=tuple(item_warnings),
    )
    validation_warnings = validate_itinerary_document(document)
    if validation_warnings:
        document.warnings = tuple(document.warnings) + validation_warnings
    return document
