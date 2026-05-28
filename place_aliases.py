"""
place_aliases.py

Nordic place database used by the itinerary parser.

Purpose:
- Normalize common ASCII spellings and recurring misspellings.
- Keep destination/city detection stable across messy supplier text.
- Prevent service phrases from becoming fake destinations.

The list intentionally focuses on places that commonly appear in Nordic travel
itineraries: cities, towns, airports, islands, regions, fjords, national parks,
and major visitor attractions/routes.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache


def _strip_accents(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", str(value or ""))
        if not unicodedata.combining(ch)
    )


def _key(value: str) -> str:
    text = _strip_accents(value).lower()
    text = text.replace("æ", "ae").replace("ø", "o").replace("å", "a")
    text = text.replace("ð", "d").replace("þ", "th")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


PLACES = [
    # Norway — main cities, towns, regions, fjords, islands and attractions
    {"country": "Norway", "canonical": "Oslo", "kind": "city", "aliases": ["Oslo City"]},
    {"country": "Norway", "canonical": "Bergen", "kind": "city", "aliases": ["Bergent"]},
    {"country": "Norway", "canonical": "Tromsø", "kind": "city", "aliases": ["Tromso", "Tromsoe"]},
    {"country": "Norway", "canonical": "Trondheim", "kind": "city", "aliases": []},
    {"country": "Norway", "canonical": "Stavanger", "kind": "city", "aliases": []},
    {"country": "Norway", "canonical": "Ålesund", "kind": "city", "aliases": ["Alesund", "Aalesund"]},
    {"country": "Norway", "canonical": "Bodø", "kind": "city", "aliases": ["Bodo", "Bodoe"]},
    {"country": "Norway", "canonical": "Narvik", "kind": "town", "aliases": []},
    {"country": "Norway", "canonical": "Alta", "kind": "town", "aliases": []},
    {"country": "Norway", "canonical": "Kirkenes", "kind": "town", "aliases": []},
    {"country": "Norway", "canonical": "Honningsvåg", "kind": "town", "aliases": ["Honningsvag"]},
    {"country": "Norway", "canonical": "Longyearbyen", "kind": "town", "aliases": []},
    {"country": "Norway", "canonical": "Svolvær", "kind": "town", "aliases": ["Svolvaer", "Svolaver", "Svoalvaer", "Svolvaerr"]},
    {"country": "Norway", "canonical": "Leknes", "kind": "town", "aliases": []},
    {"country": "Norway", "canonical": "Reine", "kind": "village", "aliases": []},
    {"country": "Norway", "canonical": "Hamnøy", "kind": "village", "aliases": ["Hamnoy"]},
    {"country": "Norway", "canonical": "Nusfjord", "kind": "village", "aliases": []},
    {"country": "Norway", "canonical": "Flåm", "kind": "village", "aliases": ["Flam"]},
    {"country": "Norway", "canonical": "Myrdal", "kind": "village", "aliases": []},
    {"country": "Norway", "canonical": "Voss", "kind": "town", "aliases": []},
    {"country": "Norway", "canonical": "Gudvangen", "kind": "village", "aliases": []},
    {"country": "Norway", "canonical": "Geiranger", "kind": "village", "aliases": []},
    {"country": "Norway", "canonical": "Åndalsnes", "kind": "town", "aliases": ["Andalsnes"]},
    {"country": "Norway", "canonical": "Molde", "kind": "town", "aliases": []},
    {"country": "Norway", "canonical": "Kristiansand", "kind": "city", "aliases": []},
    {"country": "Norway", "canonical": "Tønsberg", "kind": "city", "aliases": ["Tonsberg"]},
    {"country": "Norway", "canonical": "Drammen", "kind": "city", "aliases": []},
    {"country": "Norway", "canonical": "Fredrikstad", "kind": "city", "aliases": []},
    {"country": "Norway", "canonical": "Lillehammer", "kind": "town", "aliases": []},
    {"country": "Norway", "canonical": "Lofoten", "kind": "region", "aliases": ["Lofoten Islands"]},
    {"country": "Norway", "canonical": "Senja", "kind": "island", "aliases": []},
    {"country": "Norway", "canonical": "Vesterålen", "kind": "region", "aliases": ["Vesteralen"]},
    {"country": "Norway", "canonical": "North Cape", "kind": "attraction", "aliases": ["Nordkapp", "North Cape Norway"]},
    {"country": "Norway", "canonical": "Svalbard", "kind": "region", "aliases": []},
    {"country": "Norway", "canonical": "Oslofjord", "kind": "fjord", "aliases": ["Oslo Fjord"]},
    {"country": "Norway", "canonical": "Sognefjord", "kind": "fjord", "aliases": []},
    {"country": "Norway", "canonical": "Nærøyfjord", "kind": "fjord", "aliases": ["Naeroyfjord", "Nærøyfjorden", "Naeroyfjorden"]},
    {"country": "Norway", "canonical": "Aurlandsfjord", "kind": "fjord", "aliases": []},
    {"country": "Norway", "canonical": "Hardangerfjord", "kind": "fjord", "aliases": []},
    {"country": "Norway", "canonical": "Geirangerfjord", "kind": "fjord", "aliases": ["Geirangerfjorden"]},
    {"country": "Norway", "canonical": "Lysefjord", "kind": "fjord", "aliases": ["Lysefjorden"]},
    {"country": "Norway", "canonical": "Trollfjord", "kind": "fjord", "aliases": ["Trollfjorden"]},
    {"country": "Norway", "canonical": "Preikestolen", "kind": "attraction", "aliases": ["Pulpit Rock"]},
    {"country": "Norway", "canonical": "Kjerag", "kind": "attraction", "aliases": ["Kjeragbolten"]},
    {"country": "Norway", "canonical": "Trolltunga", "kind": "attraction", "aliases": []},
    {"country": "Norway", "canonical": "Bryggen", "kind": "attraction", "aliases": []},
    {"country": "Norway", "canonical": "Fløibanen", "kind": "attraction", "aliases": ["Floibanen", "Fløien", "Floyen", "Fløyen"]},
    {"country": "Norway", "canonical": "Fjellheisen", "kind": "attraction", "aliases": []},
    {"country": "Norway", "canonical": "Flåm Railway", "kind": "route", "aliases": ["Flam Railway", "Flåmsbana", "Flamsbana"]},
    {"country": "Norway", "canonical": "Norway in a Nutshell", "kind": "route", "aliases": ["Norway in a NUtshell", "Norway in a Nutsheel", "Norway in a Nutshel", "Norway in a NUtsheel"]},
    {"country": "Norway", "canonical": "Atlantic Road", "kind": "route", "aliases": ["Atlanterhavsveien", "Atlantic Ocean Road"]},
    {"country": "Norway", "canonical": "Oslo Airport", "kind": "airport", "aliases": ["Oslo Gardermoen", "Gardermoen Airport", "OSL"]},
    {"country": "Norway", "canonical": "Bergen Airport", "kind": "airport", "aliases": ["Bergen Flesland", "Flesland Airport", "BGO"]},
    {"country": "Norway", "canonical": "Tromsø Airport", "kind": "airport", "aliases": ["Tromso Airport", "Tromsoe Airport", "TOS"]},
    {"country": "Norway", "canonical": "Svolvær Airport", "kind": "airport", "aliases": ["Svolvaer Airport", "Svolaver Airport", "SVJ"]},
    {"country": "Norway", "canonical": "Bodø Airport", "kind": "airport", "aliases": ["Bodo Airport", "Bodoe Airport", "BOO"]},
    {"country": "Norway", "canonical": "Kirkenes Airport", "kind": "airport", "aliases": ["KKN"]},

    # Finland
    {"country": "Finland", "canonical": "Helsinki", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Rovaniemi", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Turku", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Tampere", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Oulu", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Kuopio", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Jyväskylä", "kind": "city", "aliases": ["Jyvaskyla"]},
    {"country": "Finland", "canonical": "Lahti", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Vaasa", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Porvoo", "kind": "town", "aliases": []},
    {"country": "Finland", "canonical": "Rauma", "kind": "town", "aliases": []},
    {"country": "Finland", "canonical": "Savonlinna", "kind": "town", "aliases": []},
    {"country": "Finland", "canonical": "Lappeenranta", "kind": "city", "aliases": []},
    {"country": "Finland", "canonical": "Kuusamo", "kind": "town", "aliases": []},
    {"country": "Finland", "canonical": "Kemi", "kind": "town", "aliases": []},
    {"country": "Finland", "canonical": "Levi", "kind": "resort", "aliases": []},
    {"country": "Finland", "canonical": "Kittilä", "kind": "town", "aliases": ["Kittila"]},
    {"country": "Finland", "canonical": "Ivalo", "kind": "town", "aliases": []},
    {"country": "Finland", "canonical": "Inari", "kind": "town", "aliases": []},
    {"country": "Finland", "canonical": "Saariselkä", "kind": "resort", "aliases": ["Saariselka"]},
    {"country": "Finland", "canonical": "Kakslauttanen", "kind": "resort", "aliases": ["Kakslauttenen", "Kakslautanen"]},
    {"country": "Finland", "canonical": "Ylläs", "kind": "resort", "aliases": ["Yllas"]},
    {"country": "Finland", "canonical": "Pyhä", "kind": "resort", "aliases": ["Pyha"]},
    {"country": "Finland", "canonical": "Luosto", "kind": "resort", "aliases": []},
    {"country": "Finland", "canonical": "Ranua", "kind": "town", "aliases": []},
    {"country": "Finland", "canonical": "Åland", "kind": "region", "aliases": ["Aland", "Åland Islands", "Aland Islands"]},
    {"country": "Finland", "canonical": "Finnish Lapland", "kind": "region", "aliases": ["Lapland Finland", "Finland Lapland"]},
    {"country": "Finland", "canonical": "Finnish Lakeland", "kind": "region", "aliases": ["Lakeland Finland", "Lakeland"]},
    {"country": "Finland", "canonical": "Helsinki Airport", "kind": "airport", "aliases": ["Helsinki-Vantaa", "Helsinki Vantaa", "HEL"]},
    {"country": "Finland", "canonical": "Rovaniemi Airport", "kind": "airport", "aliases": ["RVN"]},
    {"country": "Finland", "canonical": "Ivalo Airport", "kind": "airport", "aliases": ["IVL"]},
    {"country": "Finland", "canonical": "Kittilä Airport", "kind": "airport", "aliases": ["Kittila Airport", "KTT"]},
    {"country": "Finland", "canonical": "Santa Claus Village", "kind": "attraction", "aliases": ["Santa Village", "Santa Claus Village Rovaniemi"]},
    {"country": "Finland", "canonical": "Arktikum", "kind": "attraction", "aliases": ["Arktikum Museum"]},
    {"country": "Finland", "canonical": "Suomenlinna", "kind": "attraction", "aliases": []},
    {"country": "Finland", "canonical": "Temppeliaukio Church", "kind": "attraction", "aliases": ["Rock Church"]},

    # Sweden
    {"country": "Sweden", "canonical": "Stockholm", "kind": "city", "aliases": []},
    {"country": "Sweden", "canonical": "Gothenburg", "kind": "city", "aliases": ["Goteborg", "Göteborg", "Gothernburg", "Gothenbrug"]},
    {"country": "Sweden", "canonical": "Malmö", "kind": "city", "aliases": ["Malmo"]},
    {"country": "Sweden", "canonical": "Uppsala", "kind": "city", "aliases": []},
    {"country": "Sweden", "canonical": "Västerås", "kind": "city", "aliases": ["Vasteras"]},
    {"country": "Sweden", "canonical": "Örebro", "kind": "city", "aliases": ["Orebro"]},
    {"country": "Sweden", "canonical": "Linköping", "kind": "city", "aliases": ["Linkoping"]},
    {"country": "Sweden", "canonical": "Norrköping", "kind": "city", "aliases": ["Norrkoping"]},
    {"country": "Sweden", "canonical": "Umeå", "kind": "city", "aliases": ["Umea"]},
    {"country": "Sweden", "canonical": "Luleå", "kind": "city", "aliases": ["Lulea"]},
    {"country": "Sweden", "canonical": "Kiruna", "kind": "town", "aliases": []},
    {"country": "Sweden", "canonical": "Abisko", "kind": "village", "aliases": []},
    {"country": "Sweden", "canonical": "Jukkasjärvi", "kind": "village", "aliases": ["Jukkasjarvi"]},
    {"country": "Sweden", "canonical": "Boden", "kind": "town", "aliases": []},
    {"country": "Sweden", "canonical": "Haparanda", "kind": "town", "aliases": []},
    {"country": "Sweden", "canonical": "Åre", "kind": "resort", "aliases": ["Are"]},
    {"country": "Sweden", "canonical": "Visby", "kind": "town", "aliases": []},
    {"country": "Sweden", "canonical": "Gotland", "kind": "island", "aliases": []},
    {"country": "Sweden", "canonical": "Öland", "kind": "island", "aliases": ["Oland"]},
    {"country": "Sweden", "canonical": "Swedish Lapland", "kind": "region", "aliases": ["Lapland Sweden", "Sweden Lapland"]},
    {"country": "Sweden", "canonical": "Stockholm Archipelago", "kind": "region", "aliases": []},
    {"country": "Sweden", "canonical": "West Sweden", "kind": "region", "aliases": []},
    {"country": "Sweden", "canonical": "Småland", "kind": "region", "aliases": ["Smaland"]},
    {"country": "Sweden", "canonical": "Dalarna", "kind": "region", "aliases": []},
    {"country": "Sweden", "canonical": "Gamla Stan", "kind": "attraction", "aliases": ["Stockholm Old Town"]},
    {"country": "Sweden", "canonical": "Vasa Museum", "kind": "attraction", "aliases": ["Vasamuseet"]},
    {"country": "Sweden", "canonical": "ABBA The Museum", "kind": "attraction", "aliases": ["ABBA Museum"]},
    {"country": "Sweden", "canonical": "Icehotel", "kind": "hotel", "aliases": ["Ice Hotel"]},
    {"country": "Sweden", "canonical": "Treehotel", "kind": "hotel", "aliases": ["Tree Hotel"]},
    {"country": "Sweden", "canonical": "Stockholm Airport", "kind": "airport", "aliases": ["Stockholm Arlanda", "Arlanda Airport", "ARN"]},
    {"country": "Sweden", "canonical": "Gothenburg Airport", "kind": "airport", "aliases": ["Göteborg Landvetter", "Goteborg Landvetter", "Landvetter Airport", "GOT"]},
    {"country": "Sweden", "canonical": "Kiruna Airport", "kind": "airport", "aliases": ["KRN"]},

    # Iceland
    {"country": "Iceland", "canonical": "Reykjavík", "kind": "city", "aliases": ["Reykjavik"]},
    {"country": "Iceland", "canonical": "Keflavík", "kind": "town", "aliases": ["Keflavik"]},
    {"country": "Iceland", "canonical": "Akureyri", "kind": "town", "aliases": []},
    {"country": "Iceland", "canonical": "Vík", "kind": "village", "aliases": ["Vik", "Vík í Mýrdal", "Vik i Myrdal"]},
    {"country": "Iceland", "canonical": "Höfn", "kind": "town", "aliases": ["Hofn"]},
    {"country": "Iceland", "canonical": "Selfoss", "kind": "town", "aliases": []},
    {"country": "Iceland", "canonical": "Húsavík", "kind": "town", "aliases": ["Husavik"]},
    {"country": "Iceland", "canonical": "Egilsstaðir", "kind": "town", "aliases": ["Egilsstadir"]},
    {"country": "Iceland", "canonical": "Ísafjörður", "kind": "town", "aliases": ["Isafjordur"]},
    {"country": "Iceland", "canonical": "Borgarnes", "kind": "town", "aliases": []},
    {"country": "Iceland", "canonical": "Stykkishólmur", "kind": "town", "aliases": ["Stykkisholmur"]},
    {"country": "Iceland", "canonical": "Seyðisfjörður", "kind": "town", "aliases": ["Seydisfjordur"]},
    {"country": "Iceland", "canonical": "Golden Circle", "kind": "route", "aliases": []},
    {"country": "Iceland", "canonical": "South Coast", "kind": "region", "aliases": ["Iceland South Coast"]},
    {"country": "Iceland", "canonical": "Snæfellsnes", "kind": "region", "aliases": ["Snaefellsnes", "Snæfellsnes Peninsula", "Snaefellsnes Peninsula"]},
    {"country": "Iceland", "canonical": "Westfjords", "kind": "region", "aliases": ["West Fjords"]},
    {"country": "Iceland", "canonical": "Þingvellir National Park", "kind": "national_park", "aliases": ["Thingvellir", "Thingvellir National Park", "Þingvellir"]},
    {"country": "Iceland", "canonical": "Geysir", "kind": "attraction", "aliases": ["Geysir Geothermal Area"]},
    {"country": "Iceland", "canonical": "Gullfoss", "kind": "waterfall", "aliases": ["Gullfoss Waterfall"]},
    {"country": "Iceland", "canonical": "Kerið", "kind": "attraction", "aliases": ["Kerid", "Kerið Crater", "Kerid Crater"]},
    {"country": "Iceland", "canonical": "Blue Lagoon", "kind": "attraction", "aliases": ["Bluelagoon", "Blue lagoon"]},
    {"country": "Iceland", "canonical": "Sky Lagoon", "kind": "attraction", "aliases": ["Skylagoon", "Sky lagoon"]},
    {"country": "Iceland", "canonical": "Jökulsárlón", "kind": "lagoon", "aliases": ["Jokulsarlon", "Jökulsárlón Glacier Lagoon", "Jokulsarlon Glacier Lagoon"]},
    {"country": "Iceland", "canonical": "Diamond Beach", "kind": "beach", "aliases": []},
    {"country": "Iceland", "canonical": "Reynisfjara", "kind": "beach", "aliases": ["Reynisfjara Black Sand Beach"]},
    {"country": "Iceland", "canonical": "Seljalandsfoss", "kind": "waterfall", "aliases": []},
    {"country": "Iceland", "canonical": "Skógafoss", "kind": "waterfall", "aliases": ["Skogafoss"]},
    {"country": "Iceland", "canonical": "Mývatn", "kind": "lake", "aliases": ["Myvatn", "Lake Mývatn", "Lake Myvatn"]},
    {"country": "Iceland", "canonical": "Dettifoss", "kind": "waterfall", "aliases": []},
    {"country": "Iceland", "canonical": "Goðafoss", "kind": "waterfall", "aliases": ["Godafoss"]},
    {"country": "Iceland", "canonical": "Vatnajökull", "kind": "national_park", "aliases": ["Vatnajokull", "Vatnajökull National Park", "Vatnajokull National Park"]},
    {"country": "Iceland", "canonical": "Skaftafell", "kind": "region", "aliases": []},
    {"country": "Iceland", "canonical": "Landmannalaugar", "kind": "region", "aliases": []},
    {"country": "Iceland", "canonical": "Keflavík Airport", "kind": "airport", "aliases": ["Keflavik Airport", "KEF"]},
    {"country": "Iceland", "canonical": "Reykjavík Airport", "kind": "airport", "aliases": ["Reykjavik Airport", "RKV"]},
    {"country": "Iceland", "canonical": "Akureyri Airport", "kind": "airport", "aliases": ["AEY"]},

    # Denmark
    {"country": "Denmark", "canonical": "Copenhagen", "kind": "city", "aliases": ["København", "Kobenhavn"]},
    {"country": "Denmark", "canonical": "Aarhus", "kind": "city", "aliases": ["Århus", "Arhus"]},
    {"country": "Denmark", "canonical": "Odense", "kind": "city", "aliases": []},
    {"country": "Denmark", "canonical": "Aalborg", "kind": "city", "aliases": ["Ålborg", "Alborg"]},
    {"country": "Denmark", "canonical": "Billund", "kind": "town", "aliases": []},
    {"country": "Denmark", "canonical": "Roskilde", "kind": "city", "aliases": []},
    {"country": "Denmark", "canonical": "Helsingør", "kind": "town", "aliases": ["Helsingor", "Elsinore"]},
    {"country": "Denmark", "canonical": "Skagen", "kind": "town", "aliases": []},
    {"country": "Denmark", "canonical": "Ribe", "kind": "town", "aliases": []},
    {"country": "Denmark", "canonical": "Esbjerg", "kind": "city", "aliases": []},
    {"country": "Denmark", "canonical": "Kolding", "kind": "city", "aliases": []},
    {"country": "Denmark", "canonical": "Vejle", "kind": "city", "aliases": []},
    {"country": "Denmark", "canonical": "Frederiksberg", "kind": "city", "aliases": []},
    {"country": "Denmark", "canonical": "Bornholm", "kind": "island", "aliases": []},
    {"country": "Denmark", "canonical": "North Zealand", "kind": "region", "aliases": ["Nordsjælland", "Nordsjaelland"]},
    {"country": "Denmark", "canonical": "Funen", "kind": "island", "aliases": ["Fyn"]},
    {"country": "Denmark", "canonical": "Jutland", "kind": "region", "aliases": ["Jylland"]},
    {"country": "Denmark", "canonical": "Zealand", "kind": "island", "aliases": ["Sjælland", "Sjaelland"]},
    {"country": "Denmark", "canonical": "Tivoli Gardens", "kind": "attraction", "aliases": ["Tivoli"]},
    {"country": "Denmark", "canonical": "Nyhavn", "kind": "attraction", "aliases": []},
    {"country": "Denmark", "canonical": "Amalienborg", "kind": "attraction", "aliases": ["Amalienborg Palace"]},
    {"country": "Denmark", "canonical": "Christiansborg", "kind": "attraction", "aliases": ["Christiansborg Palace"]},
    {"country": "Denmark", "canonical": "Rosenborg Castle", "kind": "attraction", "aliases": ["Rosenborg"]},
    {"country": "Denmark", "canonical": "The Little Mermaid", "kind": "attraction", "aliases": ["Little Mermaid"]},
    {"country": "Denmark", "canonical": "Kronborg Castle", "kind": "attraction", "aliases": ["Kronborg"]},
    {"country": "Denmark", "canonical": "LEGOLAND Billund", "kind": "attraction", "aliases": ["Legoland", "Legoland Billund"]},
    {"country": "Denmark", "canonical": "Copenhagen Airport", "kind": "airport", "aliases": ["København Airport", "Kobenhavn Airport", "CPH", "Kastrup Airport"]},
    {"country": "Denmark", "canonical": "Billund Airport", "kind": "airport", "aliases": ["BLL"]},
    {"country": "Denmark", "canonical": "Aalborg Airport", "kind": "airport", "aliases": ["Aalborg Lufthavn", "Aalborg Airport", "AAL"]},
]

# Phrases that frequently appear in service cells but should never become
# destination names.
SERVICE_PHRASES = [
    "private hotel to airport",
    "private airport to hotel",
    "private hotel to station",
    "private station to hotel",
    "private transfer",
    "self transfer",
    "hotel to airport",
    "airport to hotel",
    "hotel to station",
    "station to hotel",
    "optional addon",
    "optional add on",
    "optional addons",
    "arrange day wise",
    "travel element",
]


def _build_alias_maps():
    alias_to_canonical: dict[str, str] = {}
    alias_records: list[tuple[str, str]] = []

    for place in PLACES:
        canonical = place["canonical"]
        aliases = [canonical] + list(place.get("aliases", []))
        for alias in aliases:
            if not alias:
                continue
            key = _key(alias)
            if key and key not in alias_to_canonical:
                alias_to_canonical[key] = canonical
            alias_records.append((str(alias), canonical))

    # Longest first so "Keflavík Airport" wins before "Keflavík".
    alias_records = sorted(set(alias_records), key=lambda item: len(item[0]), reverse=True)
    return alias_to_canonical, alias_records


ALIAS_TO_CANONICAL, ALIAS_RECORDS = _build_alias_maps()

def _build_alias_patterns():
    patterns = []
    common_word_aliases = {"are", "in", "to", "on", "at", "by"}
    for alias, canonical in ALIAS_RECORDS:
        if alias == canonical:
            continue
        alias_key = _key(alias)
        if alias_key in common_word_aliases:
            continue
        canonical_key = _key(canonical)
        suffix_key = canonical_key[len(alias_key):].strip() if canonical_key.startswith(alias_key) else ""
        escaped = re.escape(alias)
        pattern = re.compile(rf"(?<![\wÀ-ÿ]){escaped}(?![\wÀ-ÿ])", flags=re.IGNORECASE)
        patterns.append((pattern, canonical, suffix_key))
    return patterns


ALIAS_PATTERNS = _build_alias_patterns()
CANONICAL_PLACES = {place["canonical"] for place in PLACES}
CANONICAL_TO_COUNTRY = {place["canonical"]: place["country"] for place in PLACES}
CANONICAL_TO_KIND = {place["canonical"]: place.get("kind", "") for place in PLACES}


@lru_cache(maxsize=4096)
def canonicalize_place_name(value: str) -> str:
    text = str(value or "").strip(" .,-|:")
    if not text:
        return ""

    canonical = ALIAS_TO_CANONICAL.get(_key(text))
    return canonical or text


def is_known_place(value: str) -> bool:
    return canonicalize_place_name(value) in CANONICAL_PLACES


def country_for_place(value: str) -> str:
    """Return the country for a known canonical or alias place."""
    return CANONICAL_TO_COUNTRY.get(canonicalize_place_name(value), "")


def kind_for_place(value: str) -> str:
    """Return the place kind for a known canonical or alias place."""
    return CANONICAL_TO_KIND.get(canonicalize_place_name(value), "")


def is_likely_service_text(value: str) -> bool:
    text = _key(value)
    if not text:
        return False
    if any(phrase in text for phrase in [_key(item) for item in SERVICE_PHRASES]):
        return True
    if " to " in f" {text} " and any(word in text for word in ["airport", "hotel", "station", "accommodation"]):
        return True
    return False


def normalize_place_text(value: str) -> str:
    """Replace known place aliases inside free text while preserving other text."""

    text = str(value or "")
    if not text:
        return text

    # Normalize punctuation variants before alias replacement.
    text = text.replace("–", "-").replace("—", "-")

    for pattern, canonical, suffix_key in ALIAS_PATTERNS:
        def replace_alias(match, canonical=canonical, suffix_key=suffix_key):
            # If an alias is already followed by the canonical suffix, do not
            # expand it again. This prevents generic rules such as
            # "Thingvellir" -> "Þingvellir National Park" from producing
            # "Þingvellir National Park National Park" on later passes.
            if suffix_key:
                following = text[match.end(): match.end() + len(suffix_key) + 8]
                if _key(following).startswith(suffix_key):
                    return match.group(0)
            return canonical

        text = pattern.sub(replace_alias, text)

    # Final defensive cleanup for duplicated place-type suffixes that may come
    # from messy supplier text or repeated alias normalisation.
    text = re.sub(r"\b(National Park)(?:\s+\1)+\b", r"\1", text, flags=re.IGNORECASE)

    return text
