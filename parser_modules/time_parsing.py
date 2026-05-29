"""Backward-compatible facade for parser time helpers."""

from __future__ import annotations

from parser_modules.time_tokens import (
    format_12_hour,
    format_time_token,
    infer_range_suffixes,
    normalize_ampm,
    parse_time_token,
)
from parser_modules.time_finders import find_clock_range, find_single_clock_time
from parser_modules.time_normalize import normalize_time_text
from parser_modules.time_duration import normalize_duration_text, split_time_and_duration
