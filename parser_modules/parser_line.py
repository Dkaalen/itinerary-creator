"""Single-line helpers for the top-level parser."""

from __future__ import annotations

from parser_modules.common import clean_space
from parser_modules.rows import find_day_index


def split_optional_marker(parts: list[str]) -> tuple[list[str], bool]:
    if parts and parts[0] in {"__OPTIONAL__", "__MAIN__"}:
        return parts[1:], parts[0] == "__OPTIONAL__"
    return parts, False


def line_parts(raw_line: str) -> tuple[list[str], bool]:
    parts = raw_line.rstrip("\n").split("\t")
    return split_optional_marker(parts)


def has_content(parts: list[str]) -> bool:
    return any(part.strip() for part in parts)


def day_from_parts(parts: list[str]) -> tuple[int | None, str]:
    day_index = find_day_index(parts)
    if day_index is None:
        return None, ""
    return day_index, clean_space(parts[day_index])
