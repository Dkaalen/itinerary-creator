"""Public compatibility facade for transport rendering."""

from itinerary_generation.transport_domain.nutshell_render import norway_nutshell_lines
from itinerary_generation.transport_domain.render_arrangements import build_travel_arrangements_render_block, get_travel_arrangement_line, travel_row_lines as _travel_row_lines
from itinerary_generation.transport_domain.render_sequences import get_travel_sequence_line, is_travel_sequence_candidate
from itinerary_generation.transport_domain.render_special_routes import inline_arrival_time as _inline_arrival_time


def _norway_nutshell_lines(row):
    return norway_nutshell_lines(row, inline_arrival_time_func=_inline_arrival_time)


__all__ = ["_norway_nutshell_lines", "build_travel_arrangements_render_block", "get_travel_arrangement_line", "get_travel_sequence_line", "is_travel_sequence_candidate"]
