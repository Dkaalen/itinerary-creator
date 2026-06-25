"""Structured travel-sequence builders."""

from __future__ import annotations

import re

from itinerary_generation.common import get_row_type, is_self_arranged
from itinerary_generation.structured_days_builder import _day_number
from itinerary_generation.structured_model import TravelLeg, TravelSequence
from itinerary_generation.structured_row_helpers import _clean, _row_id
from itinerary_generation.time_display import display_time
from itinerary_generation.transport_model import get_transport_source_text, is_cruise_leisure_row, is_transport_like_row
from itinerary_generation.transport_norway import _is_norway_in_a_nutshell_text
from itinerary_generation.transport_times import get_transport_time_text

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

__all__ = [
    "_travel_place_pair",
    "_transport_kind_label",
    "_travel_leg",
    "_is_travel_row",
    "_sequence_destination",
    "_primary_mode",
    "_build_travel_sequences",
]
