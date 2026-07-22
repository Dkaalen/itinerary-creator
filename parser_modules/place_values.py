"""Parser place-value validation and normalization."""
from __future__ import annotations

import re

from place_aliases import canonicalize_place_name, is_likely_service_text
from .text_cleanup import clean_space, fix_common_text
from .type_detection import looks_like_day, looks_like_date, looks_like_known_type

INVALID_CITY_VALUES = {"eur", "nok", "sek", "dkk", "isk", "usd", "gbp"}

INVALID_CITY_MARKERS = [
    "private hotel",
    "private airport",
    "hotel to airport",
    "airport to hotel",
    "optional addon",
    "optional add on",
    "optinal addon",
    "addon on request",
    "flight ",
    "activity upgrade",
    "actvity upgrade",
    "transfer package",
    "shuttle transfer",
]

_INVALID_ROUTE_ORIGINS = {
    "",
    "drive",
    "flight",
    "train",
    "transfer",
    "shuttle transfer",
    "self transfer",
    "coach",
    "bus",
    "ferry",
    "cruise",
    "scenic train",
    "scenic train transfer",
    "long distance panorama coach transfer",
    "atlantic ocean cruise",
    "arrival",
}
_INVALID_ROUTE_DESTINATIONS = {"hotel", "station", "airport", "accommodation"}
_ROUTE_MODE_PREFIX_RE = re.compile(
    r"^(?:scenic\s+)?(?:flight|train|coach|bus|ferry|cruise)(?:\s+transfer)?\s*[:|]?\s*",
    flags=re.IGNORECASE,
)
_ROUTE_DETAIL_SPLIT_RE = re.compile(
    r"\s+-\s+(?:departure|arrival|time|includes|included|excludes|luggage|cabin)\b|"
    r"\s+\|\s+(?:departure|arrival|time|includes|included|excludes|final\s+timing|voucher)\b",
    flags=re.IGNORECASE,
)
_ROUTE_TRAILING_DETAIL_RE = re.compile(
    r"\s+part\s+\d+\b|\s+\d{1,2}:\d{2}|\s+-\s+(?:bus|coach|flight|train)\b|"
    r"\s+bus\s+\d+\b|\s+time\b|\s+departure\b|\s+arrival\b|\s*\|",
    flags=re.IGNORECASE,
)
_ONBOARD_DETAIL_RE = re.compile(r"\s+onboard\b|\s+on\s+board\b|\s+at\s+\d{1,2}:\d{2}", flags=re.IGNORECASE)


def is_valid_city_value(value):
    city = clean_space(value).strip(" .,-|:")
    if not city:
        return False
    lower = city.lower()
    if lower in INVALID_CITY_VALUES:
        return False
    if looks_like_day(city) or looks_like_known_type(city) or looks_like_date(city):
        return False
    if city.isdigit():
        return False
    if re.fullmatch(r"[\d\s.,]+", city):
        return False
    if re.search(r"\b\d+\s*[-/]\s*\d+\s*[- ]?star\b|\b\d+\s*[- ]?star\s+hotel\b", lower):
        return False
    if len(city) > 35:
        return False
    if re.fullmatch(r"(?:shuttle|private|self[-\s]*)?\s*(?:transfer|transport|coach|bus|flight|train|ferry|cruise)(?:\s+package)?", lower):
        return False
    if is_likely_service_text(city):
        return False
    if any(marker in lower for marker in INVALID_CITY_MARKERS):
        return False
    if " to " in lower and any(word in lower for word in ["airport", "hotel", "station", "bergen", "copenhagen", "svol"]):
        return False
    return True


def normalize_place_name(value):
    place = fix_common_text(clean_space(value))
    place = place.strip(" .,-|:")

    # Remove commercial/admin wording that can trail route places in supplier cells.
    place = re.sub(r"\bself[-\s]*(?:arranged|arrange|arrnaged|arrnage)\b", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\b(?:cost|price)\s+not\s+in(?:cl|lc)uded\b", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\bnot\s+included\b", "", place, flags=re.IGNORECASE)

    # Remove service/product wording that should not appear in clean day titles.
    place = re.sub(r"^(Flight|Bus|Coach|Train|Transfer|Shuttle Transfer)\s+", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\bArctic Resort\b", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\bAirport\s+Airport\b", "Airport", place, flags=re.IGNORECASE)
    place = re.sub(r"\s+", " ", place).strip(" .,-|:")

    return canonicalize_place_name(place)

