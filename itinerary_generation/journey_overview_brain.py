"""Journey-overview sub-brain for the summary page.

The overview table should describe how a trip unfolds.  It must not collapse a
multi-day hub stay into one random activity just because that activity has a
strong keyword.  This module owns the chapter structure and delegates compact
single-chapter wording to the existing experience classifier where appropriate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from itinerary_generation.activity_location_contract import activity_location_facts
from itinerary_generation.common import get_day_number, get_primary_city, get_row_type
from itinerary_generation.journey_overview_evidence import chapter_destination, chapter_experience
from itinerary_generation.journey_overview_variation import distinct_chapter_experience
from itinerary_generation.summaries_text import _has


@dataclass(frozen=True)
class DayOverviewFacts:
    day_key: str
    day_number: int
    city: str
    rows: tuple[dict, ...]
    has_arrival: bool
    has_departure: bool
    activity_regions: tuple[str, ...]
    activity_titles: tuple[str, ...]

    @property
    def activity_count(self) -> int:
        return len(self.activity_titles)


def format_day_range(days: Iterable[object]) -> str:
    """Return compact display text for day numbers."""

    day_numbers = [get_day_number(day) for day in days]
    day_numbers = [number for number in day_numbers if number > 0]
    if not day_numbers:
        return "TBA"
    first_day = min(day_numbers)
    last_day = max(day_numbers)
    if first_day == last_day:
        return str(first_day)
    return f"{first_day} - {last_day}"


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _activity_rows(rows: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    result: list[Mapping[str, object]] = []
    for row in rows:
        if get_row_type(dict(row)) != "Activity":
            continue
        row_kind = _clean(row.get("effective_type") or row.get("type"))
        if row_kind and row_kind.casefold() != "activity":
            continue
        text = _row_text(row).casefold()
        if "spend time at leisure" in text or "free time" in text:
            continue
        result.append(row)
    return result


def _row_text(row: Mapping[str, object]) -> str:
    return " ".join(
        [
            _clean(row.get("city", "")),
            _clean(row.get("title", "")),
            _clean(row.get("original_title", "")),
            _clean(row.get("details", "")),
            " ".join(_clean(item) for item in row.get("includes", []) or ()),
        ]
    )


def _title_for(row: Mapping[str, object]) -> str:
    return _clean(row.get("display_title") or row.get("title") or row.get("original_title") or "")


def _facts_for_day(day_key: str, rows: Sequence[dict]) -> DayOverviewFacts:
    activity_rows = _activity_rows(rows)
    regions: list[str] = []
    titles: list[str] = []
    for row in activity_rows:
        facts = activity_location_facts(row)
        title = _title_for(row)
        if title:
            titles.append(title)
        if facts.excursion_region:
            regions.append(facts.excursion_region)
    row_types = {get_row_type(row) for row in rows}
    city = get_primary_city(rows) or ("Cruise" if "Cruise" in row_types else "Journey")
    return DayOverviewFacts(
        day_key=day_key,
        day_number=get_day_number(day_key),
        city=city,
        rows=tuple(rows),
        has_arrival="Arrival" in row_types,
        has_departure="Departure" in row_types,
        activity_regions=tuple(dict.fromkeys(regions)),
        activity_titles=tuple(dict.fromkeys(titles)),
    )


def _is_hub_and_spoke(days: Sequence[DayOverviewFacts]) -> bool:
    if len(days) < 4:
        return False
    base_cities = {day.city.casefold() for day in days if day.city and not day.has_departure}
    if len(base_cities) != 1:
        return False
    excursion_regions = {region.casefold() for day in days for region in day.activity_regions}
    active_days = sum(1 for day in days if day.activity_count)
    return active_days >= 3 and len(excursion_regions) >= 2


def _country_day_trip_phrase(days: Sequence[DayOverviewFacts], base_city: str) -> str:
    text = " ".join(_row_text(row) for day in days for row in day.rows).casefold()
    if _has(text, "iceland", "reykjav", "golden circle", "jökuls", "jokuls", "snæfellsnes", "snaefellsnes"):
        return f"Iceland day-trip highlights from {base_city}"
    return f"Regional day trips from {base_city}"


def _activity_phrase_for_day(day: DayOverviewFacts) -> str:
    text = " ".join(_row_text(row) for row in day.rows).casefold()
    if day.activity_count >= 2:
        if _has(text, "whale") and _has(text, "blue lagoon"):
            return "Whale watching and Blue Lagoon"
        return chapter_experience(day.rows, day.city)
    if day.activity_regions:
        region = day.activity_regions[0]
        if region == "Fagradalsfjall and Meradalir":
            return "Volcano hiking"
        if region == "Jökulsárlón Glacier Lagoon":
            return "Glacier lagoon and boat tour"
        if region == "Iceland’s South Coast":
            return "South Coast waterfalls and black sand beach"
        return f"{region} highlights" if len(region) <= 34 else region
    return chapter_experience(day.rows, day.city)


def _chapter(chapter: str, days: Iterable[object], experience: str) -> dict[str, str]:
    return {
        "chapter": _clean(chapter),
        "days": format_day_range(days),
        "experience": _clean(experience),
    }


def _row_types(rows: Sequence[Mapping[str, object]]) -> set[str]:
    return {get_row_type(dict(row)) for row in rows}


def _has_meaningful_activity(rows: Sequence[Mapping[str, object]]) -> bool:
    return bool(_activity_rows(rows))


def _should_split_same_destination(
    current_rows: Sequence[Mapping[str, object]],
    next_rows: Sequence[Mapping[str, object]],
    city: str,
) -> bool:
    """Return whether two consecutive days in the same city need separate chapters.

    City equality is not enough to prove that days belong to one summary
    chapter.  A distinct source-backed activity day (Blue Lagoon after a
    glacier-lagoon day, for example) must remain visible in the trip overview.
    Arrival/departure days also form their own itinerary phases.
    """

    if not (_has_meaningful_activity(current_rows) and _has_meaningful_activity(next_rows)):
        return False

    combined_source = " ".join(
        _row_text(row) for row in [*current_rows, *next_rows]
    ).casefold()
    # These are deliberately compatible parts of one Oslo chapter.  Splitting
    # them loses the stronger combined summary already owned by the evidence
    # layer ("Norway in a Nutshell and Oslo food tour").
    if "norway in a nutshell" in combined_source and any(
        marker in combined_source for marker in ("food tour", "tasting", "culinary")
    ):
        return False

    # Split only when a source-backed signature experience would otherwise be
    # swallowed by a multi-day same-base chapter.  City equality alone should
    # not hide Blue Lagoon / volcano / glacier-lagoon days, but ordinary
    # complementary city activities should remain compact.
    signature_markers = (
        "blue lagoon",
        "volcano eruption",
        "fagradalsfjall",
        "jökulsárlón",
        "jokulsarlon",
        "glacier lagoon",
        "golden circle",
        "snæfellsnes",
        "snaefellsnes",
    )
    current_source = " ".join(_row_text(row) for row in current_rows).casefold()
    next_source = " ".join(_row_text(row) for row in next_rows).casefold()
    return any(marker in next_source and marker not in current_source for marker in signature_markers)


def _hub_and_spoke_chapters(days: Sequence[DayOverviewFacts]) -> list[dict[str, str]]:
    base_city = next(day.city for day in days if day.city and not day.has_departure)
    chapters: list[dict[str, str]] = []
    index = 0
    if days and days[0].has_arrival:
        chapters.append(_chapter(base_city, [days[0].day_key], f"Arrival and {base_city} welcome"))
        index = 1
    active = [day for day in days[index:] if day.activity_count and not day.has_departure]
    early_multi = []
    if active and active[0].activity_count >= 2:
        early_multi = [active[0]]
        chapters.append(_chapter(base_city, [active[0].day_key], _activity_phrase_for_day(active[0])))
    remaining = [day for day in active if day not in early_multi]
    if remaining:
        chapters.append(_chapter(base_city, [day.day_key for day in remaining], _country_day_trip_phrase(remaining, base_city)))
    departure_days = [day for day in days if day.has_departure]
    for day in departure_days:
        chapters.append(_chapter(day.city or base_city, [day.day_key], f"Departure from {day.city or base_city}"))
    return chapters


def create_journey_overview(grouped_days: Mapping[str, Sequence[dict]]) -> list[dict[str, str]]:
    """Return the summary-page journey overview chapters."""

    day_facts = [_facts_for_day(day, list(rows)) for day, rows in grouped_days.items()]
    if _is_hub_and_spoke(day_facts):
        return _hub_and_spoke_chapters(day_facts)

    chapters: list[dict[str, str]] = []
    used_experiences: set[str] = set()
    seen_chapters: set[str] = set()
    current_city: str | None = None
    current_days: list[str] = []
    current_rows: list[dict] = []
    for day, rows in grouped_days.items():
        city = chapter_destination(rows) or ("Cruise" if any(get_row_type(row) == "Cruise" for row in rows) else "Journey")
        if current_city is None:
            current_city = city
            current_days = [day]
            current_rows = list(rows)
        elif city == current_city and not _should_split_same_destination(current_rows, rows, city):
            current_days.append(day)
            current_rows.extend(rows)
        else:
            chapters.append(
                _chapter(
                    current_city,
                    current_days,
                    distinct_chapter_experience(
                        current_rows, current_city, chapter_experience(current_rows, current_city),
                        used=used_experiences, seen_chapters=seen_chapters,
                    ),
                )
            )
            current_city = city
            current_days = [day]
            current_rows = list(rows)
    if current_city is not None:
        chapters.append(
            _chapter(
                current_city,
                current_days,
                distinct_chapter_experience(
                    current_rows, current_city, chapter_experience(current_rows, current_city),
                    used=used_experiences, seen_chapters=seen_chapters,
                ),
            )
        )
    return chapters


__all__ = ["DayOverviewFacts", "create_journey_overview", "format_day_range"]
