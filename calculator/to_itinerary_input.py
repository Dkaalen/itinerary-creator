"""Convert calculator rows into raw itinerary input text."""

from __future__ import annotations

import re
from typing import Iterable

from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow

_EMPTY_TYPES = {"", "total", "subtotal", "sub total"}
_DAY_RE = re.compile(r"^day\s+\d+", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]")
_METADATA_TOKENS = {"general inputs", "url"}
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def calculator_state_to_raw_input(state: CalculatorState) -> str:
    """Return tab-separated itinerary input for the existing parser pipeline."""

    return calculator_rows_to_raw_input(state.rows)


def calculator_rows_to_raw_input(rows: Iterable[CalculatorRow]) -> str:
    """Return tab-separated itinerary input for calculator rows."""

    lines = [_row_to_raw_line(row, index) for index, row in enumerate(rows, start=1) if row_is_generatable(row)]
    return "\n".join(line for line in lines if line)


def row_is_generatable(row: CalculatorRow) -> bool:
    """Return whether a calculator row has enough itinerary content to generate."""

    row_type = _clean(row.type).lower()
    if row_type in _EMPTY_TYPES:
        return False
    return bool(_clean(row.type) and _clean(row.travel_element))


def generatable_row_count(rows: Iterable[CalculatorRow]) -> int:
    """Return the number of rows that can become itinerary input lines."""

    return sum(1 for row in rows if row_is_generatable(row))


def _row_to_raw_line(row: CalculatorRow, index: int) -> str:
    day = _normalise_day(row.day, fallback_index=index)
    row_type = _clean(row.type)
    description = _build_description(row)
    cells = [
        day,
        row_type,
        "",
        _clean(row.from_date),
        _clean(row.to_date),
        _clean(row.from_time),
        _clean(row.to_time),
        _clean_supplier(row.supplier),
        description,
    ]
    return "\t".join(cells).rstrip("\t")


def _build_description(row: CalculatorRow) -> str:
    title = _clean_client_text(row.travel_element)
    details = []
    time_text = _time_text(row.from_time, row.to_time)
    if time_text:
        details.append(f"Time: {time_text}")
    comments = _clean_client_text(row.comments)
    if comments:
        details.append(comments)
    url = _clean(row.url)
    if _URL_RE.match(url):
        details.append(f"URL: {url}")
    if not details:
        return title
    return f"{title} - " + " - ".join(details)


def _normalise_day(value: object, *, fallback_index: int) -> str:
    text = _clean(value)
    if _DAY_RE.match(text):
        return text
    if text.isdigit():
        return f"Day {int(text)}"
    return f"Day {fallback_index}"


def _time_text(from_time: object, to_time: object) -> str:
    start = _clean(from_time)
    end = _clean(to_time)
    if start and end:
        return f"{start} - {end}"
    return start or end


def _clean_client_text(value: object) -> str:
    text = _clean(value)
    if not text:
        return ""
    text = _PLACEHOLDER_RE.sub("", text)
    parts = []
    for part in re.split(r"\s+-\s+|\s+·\s+", text):
        cleaned = _clean(part)
        if not cleaned or cleaned.casefold() in _METADATA_TOKENS:
            continue
        parts.append(cleaned)
    if not parts:
        return ""
    text = " - ".join(parts)
    text = re.sub(r"\bto\s*(?:-|$)", "", text, flags=re.IGNORECASE).strip(" -")
    return _clean(text)


def _clean_supplier(value: object) -> str:
    text = _clean(value)
    return "" if text.casefold() in _METADATA_TOKENS else text


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())
