"""Day-render block ordering and source-row placement."""

from __future__ import annotations

import re

from itinerary_generation.canonical_accommodation import canonical_accommodation_block
from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.canonical_builder import should_hide_note_row
from itinerary_generation.canonical_render_adapter import render_block_from_canonical
from itinerary_generation.common import get_primary_city, get_row_type, is_optional_row
from itinerary_generation.content_engine import group_tour_pickup_window_from_overview, is_group_tour_overview
from itinerary_generation.day_overview_blocks import build_day_overview_render_block
from itinerary_generation.day_planner import plan_day
from itinerary_generation.day_render_activity_blocks import (
    _is_blank_activity_row,
    build_cruise_leisure_render_block,
    build_included_today_render_block,
    build_leisure_render_block,
    build_optional_render_block,
)
from itinerary_generation.day_render_transport_blocks import build_arrival_render_block, build_departure_render_block
from itinerary_generation.group_tour_rendering import build_group_tour_day_render_block, is_group_tour_commercial_day_visible
from itinerary_generation.structured_model import TravelSequence
from itinerary_generation.transport_render_blocks import is_cruise_leisure_row
from itinerary_generation.travel_sequence_blocks import build_travel_arrangements_render_block, is_travel_sequence_candidate
from shared.source_rows import rows_by_source_id, source_row_id
from text_polish import polish_title


def _group_tour_start_time(rows):
    for row in rows:
        pickup = group_tour_pickup_window_from_overview(row)
        if pickup:
            return pickup
    return ""


def _is_group_tour_overview_row(row):
    return is_group_tour_overview(row)


def _row_id(row: dict, fallback_index: int = 0) -> str:
    return source_row_id(row, fallback_index)


def _travel_sequence_indexes(travel_sequences):
    sequence_by_first_row = {
        str(sequence.source_row_ids[0]): sequence
        for sequence in (travel_sequences or [])
        if sequence.source_row_ids
    }
    sequence_row_ids = {
        str(row_id)
        for sequence in (travel_sequences or [])
        for row_id in sequence.source_row_ids
    }
    return sequence_by_first_row, sequence_row_ids


def _flush_travel_group(blocks: list, travel_group: list[dict]) -> None:
    if not travel_group:
        return
    block = build_travel_arrangements_render_block(travel_group)
    if block:
        blocks.append(block)
    travel_group.clear()


def _append_sequence_block(blocks: list, sequence, sequence_rows: list[dict]) -> None:
    block = build_travel_arrangements_render_block(sequence_rows)
    if not block:
        return
    block.row_id = sequence.sequence_id
    block.source_row_ids = list(sequence.source_row_ids)
    block.warnings.extend(
        warning
        for warning in [
            "Travel sequence has no final destination; review source route endpoints." if not sequence.final_destination else "",
        ]
        if warning
    )
    blocks.append(block)


def _departure_transfer_row(row: dict, rows) -> dict:
    if "to your accommodation" not in str(row.get("title", "")).lower():
        return row
    row = dict(row)
    city = get_primary_city(rows) or row.get("city", "")
    row["title"] = f"Private transfer from your hotel to {polish_title(city)} Airport" if city else "Private transfer from your hotel to the airport"
    return row


def _append_regular_row_block(
    blocks: list,
    *,
    row: dict,
    rows,
    main_rows,
    day_plan,
    has_activity: bool,
    group_tour_start_time: str,
) -> None:
    row_type = get_row_type(row)
    title = row.get("title", "")

    if row_type == "Departure":
        generic_departure = re.search(r"^(departure|departure\s+day|departure\s+home|journey\s+home)$", str(title).strip(), flags=re.IGNORECASE)
        if not generic_departure:
            blocks.append(build_departure_render_block(row))
    elif row_type == "Day Overview":
        if has_activity and _is_group_tour_overview_row(row):
            return
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
        generic_arrival = re.search(r"^(arrival|welcome\s+to\s+.+)$", str(title).strip(), flags=re.IGNORECASE)
        if not generic_arrival:
            blocks.append(build_arrival_render_block(row))
    elif row_type == "Group Tour" or row.get("group_tour_role") == "day_segment":
        block = build_group_tour_day_render_block(row)
        if block:
            blocks.append(block)
    elif row_type == "Activity":
        if _is_blank_activity_row(row):
            return
        if group_tour_start_time and not row.get("time"):
            row = dict(row)
            row["group_tour_pickup_range"] = group_tour_start_time
        blocks.append(render_block_from_canonical(canonical_activity_block(row)))
    elif row_type == "Leisure":
        if day_plan.suppress_free_time:
            return
        blocks.append(build_leisure_render_block(row, main_rows))
    elif row_type in {"Notes", "Note"}:
        return
    elif is_cruise_leisure_row(row):
        blocks.append(build_cruise_leisure_render_block(row))
    elif title:
        included_block = build_included_today_render_block([polish_title(title)])
        if included_block:
            blocks.append(included_block)


def build_day_render_blocks(rows, travel_sequences: list[TravelSequence] | tuple[TravelSequence, ...] | None = None):
    """Build day blocks in source order as UI-neutral render blocks."""

    blocks = []
    travel_group: list[dict] = []
    sequence_by_first_row, sequence_row_ids = _travel_sequence_indexes(travel_sequences)
    row_lookup = rows_by_source_id(rows)
    main_rows = [row for row in rows if not is_optional_row(row)] or list(rows)
    day_plan = plan_day(main_rows)
    if day_plan.consolidate_travel and not sequence_by_first_row:
        sequence_row_ids = set()
    departure_day = any(get_row_type(row) == "Departure" for row in main_rows)
    has_activity = any(get_row_type(row) == "Activity" and not _is_blank_activity_row(row) for row in main_rows)
    group_tour_start_time = _group_tour_start_time(main_rows)

    for source_row in rows:
        row = source_row
        if row.get("group_tour_role") == "package_master" or not is_group_tour_commercial_day_visible(row):
            continue

        if is_optional_row(row):
            _flush_travel_group(blocks, travel_group)
            blocks.append(build_optional_render_block(row))
            continue

        current_row_id = _row_id(row)
        if current_row_id in sequence_by_first_row:
            sequence = sequence_by_first_row[current_row_id]
            sequence_rows = [row_lookup[row_id] for row_id in sequence.source_row_ids if row_id in row_lookup]
            if travel_group:
                for sequence_row in sequence_rows:
                    if sequence_row not in travel_group:
                        travel_group.append(sequence_row)
                continue
            _flush_travel_group(blocks, travel_group)
            _append_sequence_block(blocks, sequence, sequence_rows)
            continue
        if current_row_id in sequence_row_ids:
            continue

        row_type = get_row_type(row)
        if day_plan.consolidate_travel and (row_type == "Leisure" or _is_blank_activity_row(row)):
            continue

        if is_travel_sequence_candidate(row):
            travel_group.append(_departure_transfer_row(row, rows) if departure_day and row_type == "Transfer" else row)
            continue

        _flush_travel_group(blocks, travel_group)
        if row_type in {"Notes", "Note"} and should_hide_note_row(row):
            continue
        _append_regular_row_block(
            blocks,
            row=row,
            rows=rows,
            main_rows=main_rows,
            day_plan=day_plan,
            has_activity=has_activity,
            group_tour_start_time=group_tour_start_time,
        )

    _flush_travel_group(blocks, travel_group)
    return blocks


__all__ = ["_group_tour_start_time", "_is_group_tour_overview_row", "_row_id", "build_day_render_blocks"]
