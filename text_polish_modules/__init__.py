"""Public text-polish package exports."""

from __future__ import annotations

from text_polish_modules.text_cleanup import (
    clean_space,
    dedupe_or_similar,
    polish_client_text,
    polish_hotel_name,
    remove_duplicate_service_phrase,
)
from text_polish_modules.prices import strip_price_fragments
from text_polish_modules.titles import polish_title, sentence_style_title
from text_polish_modules.inclusions import (
    expand_compound_inclusion_item,
    polish_inclusion_item,
    polish_inclusion_items,
)
from time_duration import (
    parse_duration_minutes,
    format_duration_display,
    format_duration_minutes,
)
from time_clock import expand_time_with_duration

__all__ = [
    "clean_space",
    "dedupe_or_similar",
    "polish_client_text",
    "polish_hotel_name",
    "remove_duplicate_service_phrase",
    "strip_price_fragments",
    "polish_title",
    "sentence_style_title",
    "expand_compound_inclusion_item",
    "polish_inclusion_item",
    "polish_inclusion_items",
    "parse_duration_minutes",
    "format_duration_display",
    "format_duration_minutes",
    "expand_time_with_duration",
]
