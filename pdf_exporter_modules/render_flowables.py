"""Compatibility facade for small ReportLab flowables and rules."""

from .decorative_flowables import CoverEmblem, CenterDiamondRule, add_cover_rule, add_day_opener_rule, add_premium_rule
from .render_tables import boxed_story_table

__all__ = [
    "CenterDiamondRule",
    "CoverEmblem",
    "add_cover_rule",
    "add_day_opener_rule",
    "add_premium_rule",
    "boxed_story_table",
]
