"""Curated Fjord Tours activity knowledge used for safer product matching.

The catalogue is intentionally small and source-first.  It covers activities
shown as recommended add-ons for Norway in a Nutshell on Fjord Tours, so messy
supplier rows can keep official product identities without broad keyword rules.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class FjordToursActivity:
    rule_id: str
    display_title: str
    product_type: str
    location: str
    duration: str
    season: str
    aliases: tuple[str, ...]
    description: str
    variant_tags: tuple[str, ...] = ()


FJORDTOURS_NUTSHELL_ADDON_ACTIVITIES: tuple[FjordToursActivity, ...] = (
    FjordToursActivity(
        rule_id="flam_local_food_tasting",
        display_title="Local Food Tasting in Flåm",
        product_type="food_tasting",
        location="Flåm",
        duration="1 hr",
        season="1 May - 1 October",
        aliases=("local food tasting in flåm", "local food tasting in flam", "taste of the fjord", "flåm fjord farm", "flam fjord farm"),
        description=(
            "Enjoy a relaxed local food tasting at a fjord farm in Flåm, with Norwegian farm flavours, local stories and time to take in the surrounding fjord scenery."
        ),
        variant_tags=("fjordtours", "nutshell_addon", "flam", "food"),
    ),
    FjordToursActivity(
        rule_id="flam_stegastein_electric_minibus",
        display_title="Electric Minibus to Stegastein Viewpoint",
        product_type="sightseeing_activity",
        location="Flåm",
        duration="1 hr 30 min",
        season="Available all year",
        aliases=("electric minibus to stegastein", "stegastein viewpoint", "stegastein viewpoint tour", "eco-friendly flam stegastein"),
        description=(
            "Travel by guided electric minibus from Flåm to Stegastein viewpoint, with photo time above the Aurlandsfjord and local stories along the route."
        ),
        variant_tags=("fjordtours", "nutshell_addon", "flam", "viewpoint", "electric_bus"),
    ),
    FjordToursActivity(
        rule_id="naeroydalen_heritage_trail",
        display_title="Nærøydalen Heritage Trail",
        product_type="guided_hike",
        location="Multiple locations",
        duration="5 hr",
        season="15 May - 31 October",
        aliases=("nærøydalen heritage trail", "naeroydalen heritage trail", "heritage trail in nærøydalen", "heritage trail in naeroydalen"),
        description=(
            "Follow the Nærøydalen heritage landscape on a guided outdoor experience, with fjord-valley scenery, local heritage and a slower active break along the Nutshell route."
        ),
        variant_tags=("fjordtours", "nutshell_addon", "heritage", "hiking"),
    ),
    FjordToursActivity(
        rule_id="gudvangen_half_day_kayak",
        display_title="Half-Day Kayak Tour in Gudvangen",
        product_type="kayaking",
        location="Gudvangen",
        duration="4 hr 30 min",
        season="6 April - 30 September",
        aliases=("half-day kayak tour in gudvangen", "half day kayak tour in gudvangen", "sea kayak gudvangen", "kayak tour on the nærøyfjord", "kayak tour on the naeroyfjord"),
        description=(
            "Kayak from Gudvangen on the Nærøyfjord, with guide support and time close to the fjord scenery between steep mountains."
        ),
        variant_tags=("fjordtours", "nutshell_addon", "gudvangen", "kayak", "naeroyfjord"),
    ),
    FjordToursActivity(
        rule_id="flam_fjord_sauna",
        display_title="Fjord Sauna in Flåm",
        product_type="wellness",
        location="Flåm",
        duration="1 hr 30 min",
        season="Available all year",
        aliases=("fjord sauna in flåm", "fjord sauna in flam", "flåm sauna", "flam sauna"),
        description=(
            "Enjoy a fjord-side sauna session in Flåm, adding a relaxed wellness break to the rail and fjord journey."
        ),
        variant_tags=("fjordtours", "nutshell_addon", "flam", "sauna"),
    ),
    FjordToursActivity(
        rule_id="voss_gondola",
        display_title="Voss Gondola",
        product_type="ticket",
        location="Voss",
        duration="1 hr 30 min",
        season="7 January - 18 October",
        aliases=("voss gondola", "gondola in voss"),
        description=(
            "Use your Voss Gondola ticket for a mountain viewpoint visit above Voss, with time for panoramic views during the day."
        ),
        variant_tags=("fjordtours", "nutshell_addon", "voss", "gondola"),
    ),
    FjordToursActivity(
        rule_id="bergen_cornelius_dinner_cruise",
        display_title="Fjord Cruise and Dinner at Cornelius",
        product_type="food_cruise",
        location="Bergen",
        duration="5 hr",
        season="Available all year",
        aliases=("fjord cruise and dinner at cornelius", "cornelius seafood dinner", "cornelius restaurant dinner", "cornelius seafood"),
        description=(
            "Travel by boat from Bergen for a seafood dinner at Cornelius, combining a short fjord cruise with a coastal dining experience."
        ),
        variant_tags=("fjordtours", "nutshell_addon", "bergen", "food", "cruise"),
    ),
    FjordToursActivity(
        rule_id="bergen_guided_kayak_trip",
        display_title="Guided Kayak Trip in Bergen",
        product_type="kayaking",
        location="Bergen",
        duration="5 hr",
        season="1 May - 15 October",
        aliases=("guided kayak trip in bergen", "bergen kayak tour", "kayaking in bergen", "bergen kayak tour in the archipelago"),
        description=(
            "Paddle with a guide in the Bergen area, adding an active water-based perspective on the city, islands and coastal scenery."
        ),
        variant_tags=("fjordtours", "nutshell_addon", "bergen", "kayak"),
    ),
)

_BY_RULE_ID = {entry.rule_id: entry for entry in FJORDTOURS_NUTSHELL_ADDON_ACTIVITIES}


def fjordtours_activity_by_rule_id(rule_id: str) -> FjordToursActivity | None:
    return _BY_RULE_ID.get(str(rule_id or ""))


def fjordtours_activity_description(rule_id: str) -> str:
    entry = fjordtours_activity_by_rule_id(rule_id)
    return entry.description if entry else ""


def _normalise(value: str) -> str:
    text = str(value or "").lower()
    text = text.replace("å", "a").replace("æ", "ae").replace("ø", "o")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _alias_matches(alias: str, source: str) -> bool:
    return _normalise(alias) in _normalise(source)


def match_fjordtours_nutshell_addon(source: str, source_title: str = "") -> FjordToursActivity | None:
    """Return a curated Fjord Tours add-on activity when the title evidence is explicit."""

    title_source = f"{source_title} {source}".strip()
    for entry in FJORDTOURS_NUTSHELL_ADDON_ACTIVITIES:
        if any(_alias_matches(alias, title_source) for alias in entry.aliases):
            return entry
    return None
