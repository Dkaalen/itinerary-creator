"""Master-row detection and package-level text extraction for group tours."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from itinerary_generation.group_tour_constants import (
    _DECLARED_DURATION_RE,
    _GROUP_MASTER_MARKERS,
    _INCLUDES_FIELD_RE,
    _TIME_FIELD_RE,
)
from itinerary_generation.group_tour_row_helpers import _row_text, _row_type
from itinerary_generation.group_tour_text import _clean, _clean_strings, _field, _int, _section
from text_polish import polish_client_text, polish_title

def _master_candidates(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    has_group_rows = any(_row_type(row).casefold() == "group tour" for row in rows)
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    for index, row in enumerate(rows):
        row_type = _row_type(row).casefold()
        source = _row_text(row)
        lower = source.casefold()
        explicit = any(marker in lower for marker in _GROUP_MASTER_MARKERS)
        if row_type == "day overview" and explicit:
            priority = 0
        elif row_type == "activity" and explicit:
            priority = 1
        elif row_type == "activity" and has_group_rows and _DECLARED_DURATION_RE.search(source):
            priority = 2
        else:
            continue
        candidates.append((priority, index, row))
    return [row for _, _, row in sorted(candidates, key=lambda item: (item[0], item[1]))]


def is_group_tour_master_row(row: Mapping[str, Any] | None) -> bool:
    if not row:
        return False
    row_type = _row_type(row).casefold()
    source = _row_text(row).casefold()
    return row_type in {"activity", "day overview"} and any(marker in source for marker in _GROUP_MASTER_MARKERS)


def _master_title(source: str, row: Mapping[str, Any]) -> str:
    # ``travel_element`` is the supplier-owned package title in the standard
    # workbook.  Generic activity normalization may otherwise rewrite that
    # row to one of its listed attractions (for example ``Golden Circle Tour``),
    # which would collapse the multi-day product into a single-day activity.
    title = _clean(row.get("travel_element") or row.get("original_title") or row.get("title"))
    if not title:
        title = _clean(source.splitlines()[0] if source else "")
    # Remove city prefix and labelled logistics from source-title variants.
    title = re.split(r"\s+-\s+(?=(?:Meeting\s*point|Time|Includes|Overview)\s*:)", title, maxsplit=1, flags=re.I)[0]
    title = re.sub(r"^\s*(?:Group\s+Tour\s*:\s*)?[^:|]{2,40}:\s*", "", title, count=1, flags=re.I)
    title = re.sub(r"\s*\|\s*", ": ", title)
    return polish_title(_clean(title)) or "Guided Group Tour"


def _package_pickup_time(master: Mapping[str, Any], source: str) -> str:
    explicit = _field(_TIME_FIELD_RE, source) or _clean(master.get("time"))
    if explicit:
        return explicit
    # Legacy supplier overviews often place the departure after a pipe without
    # a Time label.  Treat it as a 30-minute hotel pick-up window, matching the
    # existing client contract while keeping the value package-owned.
    match = re.search(r"\|\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)\b", source)
    if not match:
        return ""
    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    suffix = match.group(3).replace(".", "").upper()
    end_hour = hour
    end_minute = minute + 30
    if end_minute >= 60:
        end_hour += 1
        end_minute -= 60
    if end_hour > 12:
        end_hour -= 12
    return f"Between {hour}:{minute:02d} {suffix} and {end_hour}:{end_minute:02d} {suffix}"


def _master_description(source: str) -> str:
    overview = _section(source, "Overview", ("What's included", "What’s included", "Not Included", "What to expect", "Please note"))
    if overview:
        return overview
    prefix = source
    includes = _INCLUDES_FIELD_RE.search(prefix)
    if includes:
        prefix = prefix[: includes.start()]
    prefix = re.sub(r"^.*?(?:Meeting\s*point|Time)\s*:[^\n-]*(?:\s+-\s+)?", "", prefix, count=1, flags=re.I | re.S)
    return polish_client_text(prefix.strip(" -|\n"))


def _master_inclusions(master: Mapping[str, Any], source: str) -> tuple[str, ...]:
    values = master.get("includes") or master.get("source_includes") or ()
    if isinstance(values, str):
        values = [values]
    result = list(_clean_strings(values))

    if not result:
        included_section = _section(source, "What's included", ("Not Included", "What to expect", "Please note"))
        if not included_section:
            included_section = _section(source, "What’s included", ("Not Included", "What to expect", "Please note"))
        if included_section:
            result.extend(_clean_strings(re.split(r"\n+|\s+-\s+", included_section)))
        else:
            raw = _field(_INCLUDES_FIELD_RE, source)
            if raw:
                result.extend(_clean_strings(part for part in raw.split(",")))

    # Some suppliers confirm package activities in the narrative rather than
    # repeating them in the bullet list. Preserve only an explicitly inclusive
    # construction; do not infer ordinary attraction mentions as inclusions.
    for match in re.finditer(
        r"included activities such as\s+(.+?)(?=\s+are (?:arranged|included)|[.!?](?:\s|$))",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        payload = _clean(match.group(1))
        result.extend(
            _clean_strings(
                part
                for part in re.split(r"\s*,\s*|\s+and\s+", payload)
                if _clean(part)
            )
        )
    return _clean_strings(result)

def _group_style(source: str) -> str:
    lower = source.casefold()
    if "small-group" in lower or "small group" in lower:
        return "guided_small_group"
    if "minibus" in lower:
        return "guided_minibus"
    return "guided_group"
