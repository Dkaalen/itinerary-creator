"""Canonical Calculator trip-date relationship helpers."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
import re
from typing import Iterable

from calculator.row_model import CalculatorRow

_DATE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(\d{1,2})[.](\d{1,2})[.](\d{4})$"), "dot"),
    (re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$"), "slash"),
    (re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$"), "dash"),
    (re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"), "iso"),
)
_DAY_PATTERN = re.compile(r"^(?:d|day)?\s*(\d+)$", re.IGNORECASE)
_DATE_MODES = frozenset({"linked", "locked"})


def parse_grid_date(value: object) -> tuple[date, str] | None:
    """Parse supported Calculator date text and retain its display format."""

    text = str(value or "").strip()
    if not text:
        return None
    for pattern, date_format in _DATE_PATTERNS:
        match = pattern.fullmatch(text)
        if not match:
            continue
        parts = tuple(int(value) for value in match.groups())
        try:
            if date_format == "iso":
                parsed = date(parts[0], parts[1], parts[2])
            else:
                parsed = date(parts[2], parts[1], parts[0])
        except ValueError:
            return None
        return parsed, date_format
    return None


def format_grid_date(value: date, date_format: str) -> str:
    """Format a date using a supported Calculator display format."""

    if date_format == "iso":
        return value.isoformat()
    separator = {"slash": "/", "dash": "-"}.get(date_format, ".")
    return f"{value.day:02d}{separator}{value.month:02d}{separator}{value.year:04d}"


def parse_day_number(value: object) -> int | None:
    """Return a positive itinerary day number from common day labels."""

    match = _DAY_PATTERN.fullmatch(str(value or "").strip())
    if not match:
        return None
    number = int(match.group(1))
    return number if number > 0 else None


def infer_trip_start_date(rows: Iterable[CalculatorRow]) -> str:
    """Infer a stable start date from Day 1, then the earliest dated row."""

    candidates: list[tuple[date, str]] = []
    for row in rows:
        parsed = parse_grid_date(row.from_date)
        if not parsed:
            continue
        if parse_day_number(row.day) == 1:
            return parsed[0].isoformat()
        candidates.append(parsed)
    if not candidates:
        return ""
    parsed, _date_format = min(candidates, key=lambda item: item[0])
    return parsed.isoformat()


def initialize_date_relationships(
    rows: Iterable[CalculatorRow],
    trip_start_date: object = "",
) -> tuple[str, tuple[CalculatorRow, ...]]:
    """Return a trip start and rows with explicit linked/locked date metadata.

    Historical rows are inferred conservatively: Day-aligned from dates and all
    valid to dates are linked; conflicting from dates are locked.
    """

    source_rows = tuple(rows)
    explicit_start = str(trip_start_date or "").strip()
    start_text = explicit_start if parse_grid_date(explicit_start) else infer_trip_start_date(source_rows)
    start_parsed = parse_grid_date(start_text)
    if not start_parsed:
        return "", source_rows
    start, _start_format = start_parsed
    normalized_start = start.isoformat()
    prepared: list[CalculatorRow] = []
    for row in source_rows:
        day_number = parse_day_number(row.day)
        from_parsed = parse_grid_date(row.from_date)
        to_parsed = parse_grid_date(row.to_date)

        from_mode = _normalized_mode(row.from_date_mode)
        from_offset = _optional_int(row.from_date_offset)
        if not from_mode:
            if not str(row.from_date or "").strip() and day_number:
                from_mode = "linked"
                from_offset = day_number - 1
            elif from_parsed and day_number and (from_parsed[0] - start).days == day_number - 1:
                from_mode = "linked"
                from_offset = day_number - 1
            elif from_parsed:
                from_mode = "locked"
                from_offset = None
            else:
                from_mode = ""
                from_offset = None
        elif from_mode == "linked" and from_offset is None:
            if day_number:
                from_offset = day_number - 1
            elif from_parsed:
                from_offset = (from_parsed[0] - start).days

        to_mode = _normalized_mode(row.to_date_mode)
        to_offset = _optional_int(row.to_date_offset)
        if not to_mode:
            if to_parsed:
                to_mode = "linked"
                to_offset = (to_parsed[0] - start).days
            else:
                to_mode = ""
                to_offset = None
        elif to_mode == "linked" and to_offset is None and to_parsed:
            to_offset = (to_parsed[0] - start).days

        prepared.append(
            replace(
                row,
                from_date_mode=from_mode,
                from_date_offset=from_offset,
                to_date_mode=to_mode,
                to_date_offset=to_offset,
            )
        )
    return normalized_start, tuple(prepared)


def shift_linked_dates(
    rows: Iterable[CalculatorRow],
    old_start_date: object,
    new_start_date: object,
) -> tuple[CalculatorRow, ...]:
    """Shift linked dates to a new authoritative trip start."""

    old_parsed = parse_grid_date(old_start_date)
    new_parsed = parse_grid_date(new_start_date)
    if not new_parsed:
        return tuple(rows)
    old_start = old_parsed[0] if old_parsed else None
    new_start, new_format = new_parsed
    shifted: list[CalculatorRow] = []
    for row in rows:
        values: dict[str, object] = {}
        for field_name in ("from_date", "to_date"):
            mode = _normalized_mode(getattr(row, f"{field_name}_mode")) or "linked"
            if mode != "linked":
                continue
            offset_name = f"{field_name}_offset"
            offset = _optional_int(getattr(row, offset_name))
            parsed = parse_grid_date(getattr(row, field_name))
            if offset is None:
                if field_name == "from_date":
                    day_number = parse_day_number(row.day)
                    if day_number:
                        offset = day_number - 1
                if offset is None and parsed and old_start:
                    offset = (parsed[0] - old_start).days
            if offset is None:
                continue
            date_format = parsed[1] if parsed else new_format
            values[field_name] = format_grid_date(new_start + timedelta(days=offset), date_format)
            values[offset_name] = offset
        shifted.append(replace(row, **values) if values else row)
    return tuple(shifted)


def _normalized_mode(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in _DATE_MODES else ""


def _optional_int(value: object) -> int | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "format_grid_date",
    "infer_trip_start_date",
    "initialize_date_relationships",
    "parse_day_number",
    "parse_grid_date",
    "shift_linked_dates",
]
