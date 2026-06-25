"""Build complete travel-arrangement blocks from transport rows."""

import re

from itinerary_generation.common import get_row_type
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.render_model import RenderBlock
from itinerary_generation.render_text_helpers import clean_space
from itinerary_generation.time_display import display_time
from itinerary_generation.transport_details import get_transport_detail_items
from itinerary_generation.transport_domain.coastal_cruise_render import build_coastal_cruise_block
from itinerary_generation.transport_domain.nutshell_render import build_featured_nutshell_block, norway_nutshell_lines
from itinerary_generation.transport_domain.render_sequences import drive_route_line, get_travel_sequence_line
from itinerary_generation.transport_domain.render_special_routes import coach_terminal_transfer_lines, inline_arrival_time, santa_claus_express_lines, self_transfer_lines
from itinerary_generation.transport_times import get_transport_time_text
from text_polish import format_duration_display, polish_client_text, polish_inclusion_items, polish_title


def get_travel_arrangement_line(row):
    if get_row_type(row) == "Drive": return drive_route_line(row)
    title = get_travel_sequence_line(row); time = display_time(get_transport_time_text(row)) or inline_arrival_time(row)
    duration, details = polish_client_text(row.get("duration", "")), []
    if time: details.append(time)
    arrival = inline_arrival_time(row)
    if arrival and arrival != time: details.append(f"arrives {arrival}")
    if get_row_type(row) == "Cruise":
        match = re.search(r"\b(?:\d+\s*x\s*)?Cabin\s*\(([^)]+)\)", f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}', flags=re.IGNORECASE)
        if match: details.append(f"{polish_title(match.group(1))} cabin")
    for item in get_transport_detail_items(row, title):
        lower = item.lower()
        if lower not in {"coach ticket included", "train ticket included", "ticket included"} and item and lower not in title.lower() and item not in details: details.append(item)
    if duration and " - " not in time:
        clean_duration = format_duration_display(duration)
        if clean_duration: details.append(clean_duration)
    if get_row_type(row) == "Flight":
        inclusion_details = [item for item in details if item.lower().startswith("flight tickets")]
        other_details = [item for item in details if item not in inclusion_details]
        line = f"{title} — {'; '.join(other_details)}" if other_details else title
        if inclusion_details:
            line += f"; Includes: {inclusion_details[0]}"
        return line
    return f"{title} — {'; '.join(details)}" if details else title


def travel_row_lines(row) -> list[str]:
    special = self_transfer_lines(row) or norway_nutshell_lines(row, inline_arrival_time_func=inline_arrival_time) or santa_claus_express_lines(row) or coach_terminal_transfer_lines(row)
    if special: return [line for line in special if line]
    line = get_travel_arrangement_line(row)
    return [line] if line else []


def _repair_case(value: str) -> str:
    text = re.sub(r"\bbus Station\b", "Bus Station", str(value or ""))
    return re.sub(r"\bthe Railway Station\b", "the railway station", re.sub(r"\bthe Bus Station\b", "the bus station", text))


def _legacy_lines(rows) -> list[str]:
    items = []
    for row in rows:
        for line in travel_row_lines(row):
            if line and line not in items: items.append(line)
    return [_repair_case(item) for item in polish_inclusion_items(items)]


def build_travel_arrangements_render_block(travel_rows):
    items = _legacy_lines(travel_rows)
    if not items: return None
    premium = build_featured_nutshell_block(travel_rows, items, travel_row_lines_func=travel_row_lines) or build_coastal_cruise_block(travel_rows, items, travel_sequence_line_func=get_travel_sequence_line, travel_arrangement_line_func=get_travel_arrangement_line)
    if premium is not None: return premium
    title = "Self-drive route" if all(get_row_type(row) == "Drive" for row in travel_rows) else "Travel Arrangements"
    return RenderBlock(kind="travel_sequence", row_id="travel-arrangements", section_title=title, lines=items, css_class="travel-sequence-block", source_row_ids=[str(row.get("row_id") or "") for row in travel_rows if row.get("row_id")])
