"""Text normalization helpers shared by group-tour domain modules."""

from __future__ import annotations

import re
from typing import Any, Sequence

from itinerary_domain.group_tour_constants import _SPACE_RE, _VALID_SEASONS

def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").replace("\xa0", " ")).strip(" \t\r\n-|:")


def _clean_strings(values: Any) -> tuple[str, ...]:
    if not values:
        return ()
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return tuple(result)


def _int(value: Any) -> int:
    try:
        return int(float(str(value or "0").replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _number_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return text
    if number == 0:
        return ""
    return str(int(number)) if number.is_integer() else str(number)

def _normalize_season(value: Any) -> str:
    text = _clean(value).casefold()
    if text in _VALID_SEASONS:
        return text
    if "summer" in text:
        return "summer"
    if "winter" in text:
        return "winter"
    if "all" in text or "year round" in text or "year-round" in text:
        return "all"
    return "unknown"


def _infer_season(source: str) -> str:
    lower = str(source or "").casefold()
    has_summer = "summer" in lower or "midnight sun" in lower
    has_winter = "winter" in lower or "ice cave" in lower or "northern lights" in lower
    if has_summer and not has_winter:
        return "summer"
    if has_winter and not has_summer:
        return "winter"
    return "unknown"


def _field(regex: re.Pattern[str], source: str) -> str:
    match = regex.search(str(source or ""))
    return _clean(match.group(1)) if match else ""



def _section(source: str, heading: str, stop_headings: Sequence[str]) -> str:
    stop = "|".join(re.escape(item) for item in stop_headings)
    pattern = re.compile(
        rf"(?:^|\n)\s*{re.escape(heading)}\s*\??\s*\n?(.*?)(?=(?:\n\s*(?:{stop})\s*\??\s*(?:\n|:))|$)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(source)
    return str(match.group(1) or "").strip() if match else ""
