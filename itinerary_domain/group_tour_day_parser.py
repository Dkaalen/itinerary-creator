"""Package-day parsing and enrichment for canonical group tours."""

from __future__ import annotations

from dataclasses import replace
import re
from typing import Any, Mapping, Sequence

from itinerary_domain.group_tour_constants import (
    _CONDITIONAL_MARKERS,
    _ICELAND_DAY_ATTRACTIONS,
    _ICELAND_ROUTE_PLACES,
    _PACKAGE_DAY_RE,
    _SENTENCE_RE,
)
from itinerary_domain.group_tour_models import GroupTourDay
from itinerary_domain.group_tour_row_helpers import (
    _group_tour_day_source,
    _itinerary_day_number,
    _row_type,
    _source_row_id,
)
from itinerary_domain.group_tour_text import _clean, _clean_strings
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title

def _package_day_parts(source: str) -> tuple[int, str, str, tuple[str, ...]]:
    match = _PACKAGE_DAY_RE.match(str(source or "").strip())
    if not match:
        return 0, "", str(source or "").strip(), ("group_tour_day_number_missing",)
    day_number = int(match.group(1))
    remainder = match.group(2).strip()
    warnings: list[str] = []

    title = ""
    description = remainder
    lines = [line.strip() for line in remainder.splitlines() if line.strip()]
    if len(lines) >= 2 and len(lines[0].split()) <= 18:
        title = lines[0]
        description = "\n".join(lines[1:])
    else:
        split = re.split(r"\s+-\s+", remainder, maxsplit=1)
        if len(split) == 2 and len(split[0].split()) <= 18:
            title, description = split[0], split[1]
        elif ":" in remainder:
            candidate, rest = remainder.split(":", 1)
            if len(candidate.split()) <= 14 and not re.match(r"^(You|We|After|Today|On|First|Start)\b", candidate, re.I):
                title, description = candidate, rest
    if not title:
        title = f"Group Tour Day {day_number}"
        warnings.append("group_tour_day_title_missing")
    return day_number, polish_title(_clean(title)), str(description or "").strip(), tuple(warnings)

def _day_candidates(rows: Sequence[Mapping[str, Any]], master: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    master_day = _itinerary_day_number(master)
    for index, row in enumerate(rows):
        if row is master:
            continue
        row_type = _row_type(row).casefold()
        source = _group_tour_day_source(row)
        match = _PACKAGE_DAY_RE.match(source.strip())
        if not match:
            continue
        package_day = int(match.group(1))
        itinerary_day = _itinerary_day_number(row)
        if row_type == "group tour":
            priority = 0
        elif row_type == "activity" and itinerary_day >= master_day:
            priority = 1
        else:
            continue
        candidates.append((package_day, priority * 10000 + index, row))

    # Deduplicate package-day rows, preferring explicit Group Tour rows.
    selected: dict[int, tuple[int, Mapping[str, Any]]] = {}
    for package_day, order, row in sorted(candidates, key=lambda item: (item[0], item[1])):
        selected.setdefault(package_day, (order, row))
    return [selected[number][1] for number in sorted(selected)]

def _day_highlights(package_day: int, inclusions: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for item in inclusions:
        match = re.match(r"\s*Day\s*(\d+)(?:\s*-\s*\d+)?\s*:\s*(.+)", item, flags=re.I)
        if match and int(match.group(1)) == package_day:
            result.append(_clean(match.group(2)))
    return _clean_strings(result)


def _sentences_with_markers(source: str, markers: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for sentence in _SENTENCE_RE.split(str(source or "")):
        clean = _clean(sentence)
        lower = clean.casefold()
        if clean and any(marker in lower for marker in markers):
            result.append(clean)
    return _clean_strings(result)


def _accommodation_note(source: str) -> str:
    candidates: list[str] = []
    for line in str(source or "").splitlines():
        for sentence in _SENTENCE_RE.split(line):
            clean = _clean(sentence)
            lower = clean.casefold()
            if clean and (
                ("night" in lower and any(marker in lower for marker in ("spend", "stay", "spent", "accommodation")))
                or ("accommodation" in lower and any(marker in lower for marker in ("breakfast", "private bathroom", "included in the price")))
            ):
                candidates.append(clean)
    if not candidates:
        return ""
    return min(candidates, key=len)


def _package_day_accommodation_hints(
    source: str,
    inclusions: Sequence[str],
) -> dict[int, str]:
    """Return source-owned overnight wording keyed by package day.

    Supplier package overviews commonly describe accommodation as ranges such
    as ``Day 2-3: West Iceland guesthouse w/breakfast``.  The first number is
    the package day after which that overnight applies.  Preserve the wording
    on the canonical package day instead of creating a synthetic Hotel product.
    """

    hints: dict[int, str] = {}
    candidates = [*str(source or "").replace("–", "-").splitlines(), *inclusions]
    for candidate in candidates:
        clean = _clean(candidate).replace("–", "-")
        match = re.match(r"^Day\s*(\d+)\s*-\s*(\d+)\s*:\s*(.+)$", clean, flags=re.I)
        if not match:
            continue
        wording = _clean(match.group(3))
        if not re.search(r"\b(hotel|guesthouse|accommodation|lodge|resort)\b", wording, flags=re.I):
            continue
        package_day = int(match.group(1))
        hints.setdefault(package_day, polish_client_text(wording))
    return hints


def _apply_package_accommodation_hints(
    day_segments: Sequence[GroupTourDay],
    source: str,
    inclusions: Sequence[str],
) -> tuple[GroupTourDay, ...]:
    hints = _package_day_accommodation_hints(source, inclusions)
    if not hints:
        return tuple(day_segments)

    updated: list[GroupTourDay] = []
    for segment in day_segments:
        hint = hints.get(segment.package_day_number, "")
        if not hint or segment.accommodation_note:
            updated.append(segment)
            continue
        route = list(segment.route)
        overnight_area = _overnight_area(hint, hint, route)
        updated.append(
            replace(
                segment,
                accommodation_note=hint,
                overnight_area=overnight_area,
            )
        )
    return tuple(updated)


def _route_points(source: str) -> tuple[str, ...]:
    matches: list[tuple[int, str]] = []
    for place in _ICELAND_ROUTE_PLACES:
        match = re.search(rf"(?<!\w){re.escape(place)}(?!\w)", source, flags=re.I)
        if match:
            matches.append((match.start(), canonicalize_place_name(place)))
    result: list[str] = []
    seen: set[str] = set()
    for _, place in sorted(matches):
        key = place.casefold()
        if key not in seen:
            seen.add(key)
            result.append(place)
    return tuple(result)


def _source_attraction_display(source: str, place: str, match: re.Match[str]) -> str:
    display = canonicalize_place_name(place)
    suffix_window = source[match.end(): match.end() + 16]
    if re.match(r"\s+waterfalls?\b", suffix_window, flags=re.IGNORECASE) and "waterfall" not in display.casefold():
        return f"{display} waterfall"
    return display


def _source_attractions(source: str) -> tuple[str, ...]:
    matches: list[tuple[int, str]] = []
    for place in _ICELAND_DAY_ATTRACTIONS:
        match = re.search(rf"(?<!\w){re.escape(place)}(?!\w)", source, flags=re.IGNORECASE)
        if match:
            matches.append((match.start(), _source_attraction_display(source, place, match)))
    result: list[str] = []
    seen: set[str] = set()
    for _, place in sorted(matches):
        key = place.casefold()
        if key not in seen:
            seen.add(key)
            result.append(place)
    return tuple(result)


def _overnight_area(source: str, accommodation_note: str, route: Sequence[str]) -> str:
    del source, route  # The overnight place must be present in the accommodation sentence itself.
    note_route = _route_points(accommodation_note)
    return note_route[-1] if note_route else ""


def _meal_markers(source: str, highlights: Sequence[str]) -> tuple[str, ...]:
    text = f"{source}\n{' '.join(highlights)}".casefold()
    result: list[str] = []
    if "breakfast" in text:
        result.append("Breakfast")
    if "lunch" in text and not re.search(r"lunch\s+(?:available|for purchase|not included)", text):
        result.append("Lunch")
    if "dinner" in text and not re.search(r"dinner\s+(?:available|for purchase|not included)", text):
        result.append("Dinner")
    return tuple(result)


def build_group_tour_day(row: Mapping[str, Any], inclusions: Sequence[str] = (), source_name: str = "") -> GroupTourDay:
    source = _group_tour_day_source(row)
    package_day, title, description, warnings = _package_day_parts(source)
    # Legacy parser rows may hold a cleaner, more complete supplier heading in
    # ``title`` while ``details`` has already been compacted.  Prefer that
    # explicit short heading, but never treat a full ``Day N: ...`` source row
    # from the workbook corpus as a title.
    explicit_title = re.sub(r"\s+Today$", "", _clean(row.get("title")), flags=re.IGNORECASE)
    source_title_tokens = {
        token.casefold()
        for token in re.findall(r"[\wÀ-ÖØ-öø-ÿÞþÆæ]+", title)
        if len(token) > 2
    }
    explicit_title_tokens = {
        token.casefold()
        for token in re.findall(r"[\wÀ-ÖØ-öø-ÿÞþÆæ]+", explicit_title)
        if len(token) > 2
    }
    if (
        explicit_title
        and not re.match(r"^Day\s*\d+\b", explicit_title, flags=re.IGNORECASE)
        and len(explicit_title.split()) <= 20
        and explicit_title.casefold() not in {"activity", "group tour"}
        and source_title_tokens.issubset(explicit_title_tokens)
    ):
        title = polish_title(explicit_title)
    itinerary_day = _itinerary_day_number(row)
    package_highlights = _day_highlights(package_day, inclusions)
    source_attractions = _source_attractions(source)
    highlights = source_attractions or package_highlights
    accommodation_note = _accommodation_note(source)
    route = list(_route_points(source))
    source_city = canonicalize_place_name(_clean(row.get("city")))
    if (
        source_city
        and source_city.casefold() not in {"iceland", "group tour"}
        and not re.fullmatch(r"day\s*\d+", source_city, flags=re.IGNORECASE)
        and source_city.casefold() not in {place.casefold() for place in route}
    ):
        route.append(source_city)
    optional_items = _sentences_with_markers(source, ("optional", "can be added", "extra is"))
    conditional_items = _sentences_with_markers(source, _CONDITIONAL_MARKERS)
    included_activities = _clean_strings(
        item
        for item in highlights
        if not re.search(
            r"\b(hotel|guesthouse|accommodation|arrival|pick[-‑ ]?up|minibus)\b",
            item,
            re.I,
        )
    )
    return GroupTourDay(
        package_day_number=package_day,
        itinerary_day_number=itinerary_day,
        title=title,
        description=description,
        route=tuple(route),
        highlights=highlights,
        included_activities=included_activities,
        meals=_meal_markers(source, highlights),
        overnight_area=_overnight_area(source, accommodation_note, route),
        accommodation_note=accommodation_note,
        optional_items=optional_items,
        conditional_items=conditional_items,
        source_row_ids=(_source_row_id(row, source_name),),
        source_text=source,
        warnings=warnings,
    )
