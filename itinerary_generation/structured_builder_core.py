"""Compatibility facade for structured itinerary document building.

Focused structured builder modules own row helpers, item building, warning
building, day building, travel sequencing and final-section wiring. This facade
keeps older imports stable.
"""

from __future__ import annotations

from collections import OrderedDict

from itinerary_generation.common import group_rows_by_day
from itinerary_generation.structured_days_builder import _build_days, _day_number
from itinerary_generation.structured_final_sections import _exclusion_sections, _inclusion_sections, _section_from_mapping, _split_structured_item
from itinerary_generation.structured_items_builder import (
    _TRANSPORT_KIND_BY_TYPE,
    _clean,
    _detail_lines,
    _document_item,
    _item_title,
    _kind_for_row,
    _row_id,
    _source_ref,
    _source_text,
)
from itinerary_generation.structured_model import ItineraryDocument, ModelWarning
from itinerary_generation.structured_row_helpers import _ACTIVITY_STRUCTURE_MARKERS, _has_structured_activity_supplier_text
from itinerary_generation.structured_travel_sequences import (
    _build_travel_sequences,
    _is_travel_row,
    _primary_mode,
    _sequence_destination,
    _transport_kind_label,
    _travel_leg,
    _travel_place_pair,
)
from itinerary_generation.structured_validation import validate_itinerary_document
from itinerary_generation.structured_warning_builder import (
    _ACTIVITY_SIGNAL_GROUPS,
    _STOP_TOKENS,
    _ambiguous_row_warnings,
    _row_data_warnings,
    _signature_tokens,
    _source_signal_warnings,
)

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

__all__ = [
    "_TRANSPORT_KIND_BY_TYPE",
    "_ACTIVITY_STRUCTURE_MARKERS",
    "_has_structured_activity_supplier_text",
    "_clean",
    "_row_id",
    "_source_text",
    "_source_ref",
    "_kind_for_row",
    "_item_title",
    "_detail_lines",
    "_ACTIVITY_SIGNAL_GROUPS",
    "_STOP_TOKENS",
    "_signature_tokens",
    "_source_signal_warnings",
    "_ambiguous_row_warnings",
    "_row_data_warnings",
    "_document_item",
    "_day_number",
    "_build_days",
    "_travel_place_pair",
    "_transport_kind_label",
    "_travel_leg",
    "_is_travel_row",
    "_sequence_destination",
    "_primary_mode",
    "_build_travel_sequences",
    "_split_structured_item",
    "_section_from_mapping",
    "_inclusion_sections",
    "_exclusion_sections",
    "build_itinerary_document",
]
