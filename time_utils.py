"""Backward-compatible facade for shared time and duration helpers."""

from __future__ import annotations

from time_text import clean_time_text
from time_duration import (
    format_duration_display,
    format_duration_minutes,
    parse_duration_minutes,
)
from time_clock import (
    expand_time_with_duration,
    has_time_alternatives,
    has_time_range,
)
