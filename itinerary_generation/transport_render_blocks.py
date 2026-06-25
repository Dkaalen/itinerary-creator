"""UI-neutral transport row render block builders."""

from __future__ import annotations

from itinerary_generation.common import get_row_type
from itinerary_generation.transport_model import is_cruise_leisure_row
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.render_model import RenderBlock, RenderMetaLine
from itinerary_generation.render_text_helpers import normalize_list
from itinerary_generation.time_display import display_time
from itinerary_generation.transport_details import format_flight_luggage_detail
from text_polish import format_duration_display, polish_inclusion_item, polish_inclusion_items, polish_title


def build_transport_render_block(row, title_override=None):
    title = polish_title(title_override or row.get("title", ""))
    time = row.get("time", "")
    duration = row.get("duration", "")
    includes = polish_inclusion_items([clean_include_item(item, title) for item in normalize_list(row.get("includes", []))], title)
    raw_luggage = row.get("luggage_included", "")
    if get_row_type(row) == "Flight":
        raw_luggage = format_flight_luggage_detail(raw_luggage or row.get("details", "")) or raw_luggage
    luggage_included = polish_inclusion_item(clean_include_item(raw_luggage, title), title)

    meta: list[RenderMetaLine] = []
    if time:
        meta.append(RenderMetaLine("Time", display_time(time)))
    if duration:
        clean_duration = format_duration_display(duration)
        if clean_duration:
            meta.append(RenderMetaLine("Duration", clean_duration))
    if luggage_included:
        meta.append(RenderMetaLine("Luggage included", luggage_included))

    return RenderBlock(
        kind="transport",
        row_id=str(row.get("row_id") or ""),
        section_title="Travel Today",
        title=title,
        meta=meta,
        includes=includes,
        css_class="transport-block",
    )


def build_self_transfer_render_block(row, title_override=None):
    title = polish_title(title_override or row.get("title", ""))
    city = polish_title(row.get("city", ""))
    meta = [RenderMetaLine("Location", city)] if city else []
    return RenderBlock(
        kind="self_transfer",
        row_id=str(row.get("row_id") or ""),
        section_title="Self Transfer",
        title=title,
        meta=meta,
        description=(
            "This is a self transfer, so please make your own way between these points. "
            "Transfer costs are not included unless specifically stated elsewhere in the itinerary."
        ),
        css_class="self-transfer-block",
    )


def build_self_arranged_travel_render_block(row, title_override=None):
    title = polish_title(title_override or row.get("title", ""))
    city = polish_title(row.get("city", ""))
    row_type = get_row_type(row).lower()
    if row_type == "flight" or "flight" in str(title).lower():
        note = "This flight is self-arranged and not included in the package price unless specifically stated."
    else:
        note = "This travel segment is self-arranged and not included in the package price unless specifically stated."
    meta = [RenderMetaLine("Destination", city)] if city else []
    return RenderBlock(
        kind="self_arranged_travel",
        row_id=str(row.get("row_id") or ""),
        section_title="Self-Arranged Travel",
        title=title,
        meta=meta,
        description=note,
        css_class="self-arranged-block",
    )
