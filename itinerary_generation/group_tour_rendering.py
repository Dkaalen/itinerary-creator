"""Public compatibility facade for group-tour presentation adapters."""

from itinerary_generation.group_tour_render_blocks import build_group_tour_day_render_block
from itinerary_generation.group_tour_render_context import group_tour_day_from_rows, group_tour_package_context_from_rows, group_tour_package_from_rows
from itinerary_generation.group_tour_render_inclusions import group_tour_package_inclusion_item, group_tour_package_route, is_group_tour_commercial_day_visible
from itinerary_generation.group_tour_render_titles import group_tour_day_city, group_tour_day_intro, group_tour_day_title

__all__ = ["build_group_tour_day_render_block", "group_tour_day_city", "group_tour_day_from_rows", "group_tour_day_intro", "group_tour_day_title", "group_tour_package_context_from_rows", "group_tour_package_from_rows", "group_tour_package_inclusion_item", "group_tour_package_route", "is_group_tour_commercial_day_visible"]
