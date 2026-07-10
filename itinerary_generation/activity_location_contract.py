"""Activity location truth contract for copy, overview, and image matching.

A supplier row often uses the overnight/base city as the row city even when the
experience is an excursion from that city.  This module owns that distinction so
intro copy, descriptions, journey overview rows, and image matching do not each
invent their own place logic.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping

from place_aliases import canonicalize_place_name
from text_polish import polish_title


@dataclass(frozen=True)
class ActivityLocationFacts:
    """Resolved place facts for one arranged activity."""

    base_city: str = ""
    pickup_city: str = ""
    excursion_region: str = ""
    attraction_places: tuple[str, ...] = ()
    image_intents: tuple[str, ...] = ()

    @property
    def is_excursion(self) -> bool:
        return bool(self.excursion_region and self.base_city and self.excursion_region.casefold() != self.base_city.casefold())

    @property
    def client_place(self) -> str:
        return self.excursion_region or self.base_city or self.pickup_city


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm(value: object) -> str:
    return _clean(value).casefold()


def _source_text(row: Mapping[str, object] | None = None, *, title: object = "", city: object = "", source_text: object = "") -> str:
    pieces: list[str] = [_clean(title), _clean(city), _clean(source_text)]
    if row:
        pieces.extend(
            [
                _clean(row.get("city", "")),
                _clean(row.get("title", "")),
                _clean(row.get("original_title", "")),
                _clean(row.get("details", "")),
                " ".join(_clean(item) for item in row.get("includes", []) or ()),
                " ".join(_clean(item) for item in row.get("notable_sights", []) or ()),
            ]
        )
    return _norm(" ".join(part for part in pieces if part))


def _base_city(row: Mapping[str, object] | None = None, *, city: object = "") -> str:
    raw = _clean(city)
    if not raw and row:
        raw = _clean(row.get("city", ""))
    return polish_title(canonicalize_place_name(raw) or raw)


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = polish_title(_clean(item)).strip(" .,-")
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return tuple(result)


def _matches(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _region_and_places(text: str) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    if _matches(text, r"\bgolden\s+circle\b", r"\bthingvellir\b", r"\bþingvellir\b", r"\bstrokkur\b", r"\bgullfoss\b"):
        return "Golden Circle", _unique(("Þingvellir", "Strokkur", "Gullfoss")), ("golden_circle", "geothermal", "waterfall")
    if _matches(text, r"\bsouth\s+coast\b", r"\bseljalandsfoss\b", r"\bsk[oó]gafoss\b", r"\breynisfjara\b", r"\bvik\b", r"\bvík\b"):
        return "Iceland’s South Coast", _unique(("Seljalandsfoss", "Skógafoss", "Reynisfjara", "Vík")), ("south_coast", "waterfall", "black_sand_beach")
    if _matches(text, r"\bsn[æa]fellsnes\b", r"\bkirkjufell\b", r"\barnarstapi\b"):
        return "Snæfellsnes Peninsula", _unique(("Snæfellsnes Peninsula", "Kirkjufell")), ("snaefellsnes", "mountain", "coast")
    if _matches(text, r"\bj[oö]kuls[aá]rl[oó]n\b", r"\bglacial\s+lagoon\b", r"\bglacier\s+lagoon\b"):
        return "Jökulsárlón Glacier Lagoon", _unique(("Jökulsárlón Glacier Lagoon", "Diamond Beach")), ("glacier_lagoon", "ice", "boat")
    if _matches(text, r"\bfagradalsfjall\b", r"\bmeradalir\b", r"\bvolcano\b"):
        return "Fagradalsfjall and Meradalir", _unique(("Fagradalsfjall", "Meradalir")), ("volcano", "hiking", "lava_field")
    if _matches(text, r"\bblue\s+lagoon\b"):
        return "Blue Lagoon", _unique(("Blue Lagoon",)), ("blue_lagoon", "geothermal", "spa")
    if _matches(text, r"\bwhale\b", r"\bmarine\s+life\b"):
        return "Reykjavík harbour and coast", _unique(("Reykjavík harbour",)), ("whale_watching", "harbour", "wildlife")
    return "", (), ()


def activity_location_facts(
    row: Mapping[str, object] | None = None,
    *,
    title: object = "",
    city: object = "",
    source_text: object = "",
) -> ActivityLocationFacts:
    """Return base/pickup/excursion place facts for an activity-like row."""

    base = _base_city(row, city=city)
    text = _source_text(row, title=title, city=base or city, source_text=source_text)
    region, places, intents = _region_and_places(text)
    pickup = base if _matches(text, r"hotel\s+pick", r"pick[- ]?up", r"from\s+central\s+reykjav") else ""
    return ActivityLocationFacts(
        base_city=base,
        pickup_city=pickup,
        excursion_region=region,
        attraction_places=places,
        image_intents=intents,
    )


def activity_client_location_phrase(facts: ActivityLocationFacts) -> str:
    """Return a concise phrase for copy that respects excursion/base city truth."""

    if facts.is_excursion and facts.base_city:
        return f"from {facts.base_city} to {facts.excursion_region}"
    if facts.excursion_region:
        return f"at {facts.excursion_region}"
    if facts.base_city:
        return f"in {facts.base_city}"
    return ""


__all__ = [
    "ActivityLocationFacts",
    "activity_client_location_phrase",
    "activity_location_facts",
]
