"""Build the structured itinerary document from normalized rows.

This is the first migration layer away from late-stage string/HTML fixes.  The
existing preview/PDF pipeline can still render as before, but new tests and new
features should target this document model first.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Iterable

from itinerary_generation.common import get_primary_city, get_row_type, group_rows_by_day, is_self_arranged
from itinerary_generation.date_formatting import format_client_date
from itinerary_generation.exclusion_sections import create_structured_whats_not_included
from itinerary_generation.structured_inclusions import build_structured_inclusion_sections
from shared.source_rows import clean_text, source_row_id, source_text
from itinerary_generation.structured_model import (
    DayDocument,
    DocumentItem,
    DocumentItemKind,
    ItineraryDocument,
    ModelWarning,
    SourceRowRef,
    StructuredListItem,
    StructuredListSection,
    TravelLeg,
    TravelSequence,
)
from itinerary_generation.structured_rendering import normalize_structured_list_sections
from itinerary_generation.structured_validation import validate_itinerary_document
from itinerary_generation.product_rules import product_warning
from itinerary_generation.transport_model import get_transport_source_text, is_cruise_leisure_row, is_transport_like_row
from itinerary_generation.transport_times import get_transport_time_text
from itinerary_generation.time_display import display_time
from itinerary_generation.transport_norway import _is_norway_in_a_nutshell_text

_TRANSPORT_KIND_BY_TYPE = {
    "Transfer": "transfer",
    "Transport": "transfer",
    "Train": "rail",
    "Flight": "flight",
    "Ferry": "ferry",
    "Cruise": "cruise",
    "Drive": "transfer",
}

_ACTIVITY_STRUCTURE_MARKERS = (
    "|",
    "what's included",
    "whats included",
    "meeting point",
    "pick up / meeting point",
    "pickup / meeting point",
    "pick-up/drop-off",
    "duration",
)


def _has_structured_activity_supplier_text(source_lower: str) -> bool:
    return sum(1 for marker in _ACTIVITY_STRUCTURE_MARKERS if marker in source_lower) >= 2


def _clean(value: object) -> str:
    return clean_text(value)


def _row_id(row: dict, fallback_index: int = 0) -> str:
    return source_row_id(row, fallback_index)


def _source_text(row: dict) -> str:
    return source_text(row, ("raw", "original_title", "title", "details"))


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
    warning_code, warning_message = product_warning(row, source)
    if warning_code:
        warnings.append(ModelWarning(
            code=warning_code,
            message=warning_message,
            source_row_ids=(row_id,),
        ))

    warnings.extend(_source_signal_warnings(title, source, row_id))

    return tuple(dict.fromkeys(warnings))




def _row_data_warnings(row: dict) -> tuple[ModelWarning, ...]:
    """Return source-data warnings that should survive into the document model."""

    row_id = _row_id(row)
    row_type = str(get_row_type(row) or "")
    source = " ".join(
        str(row.get(key, "") or "")
        for key in ("raw", "original_title", "details", "title")
        if str(row.get(key, "") or "").strip()
    )
    source_lower = source.lower()
    warnings: list[ModelWarning] = []

    if row_type == "Activity":
        time_text = str(row.get("time") or "")
        suspicious_am = re.search(r"\b(?:1|2|3|4|5):\d{2}\s*AM\b", time_text, flags=re.IGNORECASE)
        is_normal_night_activity = any(marker in source_lower for marker in [
            "northern light", "aurora", "overnight", "night train", "night cruise", "dinner cruise",
        ])
        is_daytime_product = any(marker in source_lower for marker in [
            "sightseeing", "walking tour", "city tour", "fjord cruise", "canal tour", "hop-on", "hop on",
        ])
        if suspicious_am and is_daytime_product and not is_normal_night_activity:
            warnings.append(ModelWarning(
                code="suspicious_activity_time",
                message=f"Activity time {time_text} looks unusual for a daytime sightseeing product; verify AM/PM before final output.",
                source_row_ids=(row_id,),
            ))
        product = row.get("activity_product") if isinstance(row.get("activity_product"), dict) else {}
        if not product and _has_structured_activity_supplier_text(source_lower):
            warnings.append(ModelWarning(
                code="low_confidence_activity_structure",
                message=(
                    "Structured supplier activity text did not match a known product fingerprint; "
                    "review the title, meeting point and inclusions before final output."
                ),
                source_row_ids=(row_id,),
            ))

    if row_type == "Hotel":
        hotel_name = str(row.get("hotel_name") or "").strip()
        generic_hotel_name = bool(re.fullmatch(r"(?:\d\s*[- ]?star\s+)?hotel", hotel_name, flags=re.IGNORECASE))
        if not hotel_name or generic_hotel_name:
            warnings.append(ModelWarning(
                code="missing_hotel_name",
                message="Accommodation row has no hotel name; verify supplier data before final output.",
                source_row_ids=(row_id,),
            ))

    return tuple(dict.fromkeys(warnings))

def _document_item(row: dict, fallback_index: int) -> DocumentItem:
    row_id = _row_id(row, fallback_index)
    warnings = _ambiguous_row_warnings(row) + _row_data_warnings(row)
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
        metadata={
            "activity_product": row.get("activity_product") or {},
            "route_legs": row.get("route_legs") or [],
        } if row.get("activity_product") or row.get("route_legs") else {},
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



def _travel_place_pair(row: dict) -> tuple[str, str]:
    """Best-effort route endpoints for model-level travel sequencing.

    This intentionally runs before rendering so day titles and travel grouping
    can depend on a structured sequence instead of whichever transfer happens
    to be rendered first.
    """

    text = _clean(get_transport_source_text(row) or row.get("title") or row.get("details"))
    direct_to = re.search(r"\b(?:flight|flgiht|train|ferry|cruise|coach|bus|transfer)\s*:?\s*to\s+(.+?)(?:\s*[-–—;,|]\s*|$)", text, flags=re.IGNORECASE)
    if direct_to:
        destination = _clean(direct_to.group(1)).strip(" -:|.,")
        destination = re.split(r"\b(?:flight|flgiht|train|ferry|cruise|coach|bus|transfer)\s*:?\s*to\s+", destination, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.,")
        destination = re.sub(r"\s*,?\s*(?:self[-\s]*(?:arranged|arrange)|cost not included|not included).*$", "", destination, flags=re.IGNORECASE).strip(" -:|.,")
        if destination:
            return _clean(row.get("city", "")), destination

    patterns = (
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s*[-–—;,|]\s*|$)",
        r"\b(.+?)\s+to\s+(.+?)(?:\s*[-–—;,|]\s*|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            origin = _clean(match.group(1)).strip(" -:|.,")
            destination = _clean(match.group(2)).strip(" -:|.,")
            origin = re.sub(r"^(?:train|flight|ferry|cruise|transfer|private transfer|coach|bus)\s*:?\s*", "", origin, flags=re.IGNORECASE).strip(" -:|.,")
            destination = re.split(r"\b(?:flight|flgiht|train|ferry|cruise|coach|bus|transfer)\s*:?\s*to\s+", destination, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|.,")
            destination = re.sub(r"\s*,?\s*(?:self[-\s]*(?:arranged|arrange)|cost not included|not included).*$", "", destination, flags=re.IGNORECASE).strip(" -:|.,")
            if destination:
                return origin, destination
    return _clean(row.get("city", "")), ""


def _transport_kind_label(row: dict) -> str:
    row_type = str(get_row_type(row) or "").strip()
    if row_type == "Transfer":
        text = get_transport_source_text(row).lower()
        if "train" in text:
            return "Train"
        if "flight" in text or "flgiht" in text:
            return "Flight"
        if "ferry" in text:
            return "Ferry"
        if "cruise" in text:
            return "Cruise"
    return row_type or "Travel"


def _travel_leg(row: dict, fallback_index: int) -> TravelLeg:
    row_id = _row_id(row, fallback_index)
    origin, destination = _travel_place_pair(row)
    source = get_transport_source_text(row)
    source_lower = source.lower()
    return TravelLeg(
        leg_id=f"leg-{row_id}",
        source_row_ids=(row_id,),
        day=str(row.get("day", "") or ""),
        from_place=origin,
        to_place=destination,
        transport_type=_transport_kind_label(row),
        operator=_clean(row.get("operator", "")),
        departure=display_time(get_transport_time_text(row)),
        notes=tuple(line for line in (_clean(row.get("details", "")),) if line),
        self_arranged=is_self_arranged(row),
        scenic=_is_norway_in_a_nutshell_text(source_lower) or any(marker in source_lower for marker in ("scenic", "fjord", "nutshell")),
        overnight="overnight" in source_lower or "night train" in source_lower or "night cruise" in source_lower,
    )


def _is_travel_row(row: dict) -> bool:
    if is_cruise_leisure_row(row):
        return False
    return is_transport_like_row(row, include_drive=True)


def _sequence_destination(legs: list[TravelLeg], rows: list[dict]) -> str:
    for leg in reversed(legs):
        if leg.to_place:
            return leg.to_place
    for row in reversed(rows):
        city = _clean(row.get("city", ""))
        if city:
            return city
    return ""


def _primary_mode(legs: list[TravelLeg]) -> str:
    modes = [leg.transport_type for leg in legs if leg.transport_type]
    if not modes:
        return "Travel"
    for preferred in ("Flight", "Train", "Cruise", "Ferry", "Drive", "Transfer"):
        if preferred in modes:
            return preferred
    return modes[0]


def _build_travel_sequences(grouped_days: dict[str, list[dict]], row_ids_by_object: dict[int, str]) -> tuple[TravelSequence, ...]:
    sequences: list[TravelSequence] = []
    for day, rows in grouped_days.items():
        current_rows: list[dict] = []

        def flush() -> None:
            nonlocal current_rows
            if not current_rows:
                return
            legs = [_travel_leg(row, index) for index, row in enumerate(current_rows)]
            source_ids = tuple(row_ids_by_object.get(id(row), _row_id(row, index)) for index, row in enumerate(current_rows))
            sequence_index = len([sequence for sequence in sequences if sequence.day == str(day)]) + 1
            sequences.append(TravelSequence(
                sequence_id=f"travel-sequence-{_day_number(str(day))}-{sequence_index}",
                day=str(day),
                source_row_ids=source_ids,
                final_destination=_sequence_destination(legs, current_rows),
                primary_travel_mode=_primary_mode(legs),
                legs=tuple(legs),
                self_arranged=any(leg.self_arranged for leg in legs),
                scenic=any(leg.scenic for leg in legs),
                overnight=any(leg.overnight for leg in legs),
            ))
            current_rows = []

        for row in rows:
            if _is_travel_row(row):
                current_rows.append(row)
            else:
                flush()
        flush()
    return tuple(sequences)

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
    travel_sequences = _build_travel_sequences(grouped, row_ids_by_object)

    item_warnings: list[ModelWarning] = []
    for item in items:
        item_warnings.extend(item.warnings)

    document = ItineraryDocument(
        source_rows=source_rows,
        days=days,
        items=items,
        inclusions=_inclusion_sections(rows, grouped),
        exclusions=_exclusion_sections(rows),
        travel_sequences=travel_sequences,
        warnings=tuple(item_warnings),
    )
    validation_warnings = validate_itinerary_document(document)
    if validation_warnings:
        document.warnings = tuple(document.warnings) + validation_warnings
    return document
