"""Hotel-name validation and extraction from supplier source text."""

import re

from normalizer_modules.hotel_rooms import ROOM_UNIT_PATTERN
from normalizer_modules.text_utils import clean_space
from place_aliases import canonicalize_place_name
from text_polish import polish_hotel_name


def is_placeholder_hotel_name(name: str, city: str = "") -> bool:
    text, city_text = clean_space(name), clean_space(city)
    if not text: return True
    lower = text.lower()
    if city_text and lower in {city_text.lower(), canonicalize_place_name(city).lower()}: return True
    if re.search(r"\b\d\s*[- ]?star\b", lower) or re.search(r"\b\d+\s*(?:x\s*)?(?:night|ngiht|nite|nt)s?", lower): return True
    if any(marker in lower for marker in ("standard room", "standard double room", "incl breakfast", "incl brekafast", "breakfast", "room category")): return True
    return lower in {"hotel", "accommodation", "or similar", "similar"}


def _strip_city_and_star_prefix(value: str, city: str = "") -> str:
    text = clean_space(value)
    if city: text = re.sub(rf"^\s*{re.escape(city)}\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,40}\s*:\s*", "", text)
    return clean_space(re.sub(r"^\s*[2-5]\s*[- ]?star\s*", "", text, flags=re.IGNORECASE).strip(" ,-:"))


def _looks_like_room_fragment(value: str) -> bool:
    lower = clean_space(value).lower()
    if "hotel" in lower and not re.search(r"\d+\s*x", lower): return False
    return bool(re.search(r"\d+\s*x\s*", lower) or re.search(rf"\b{ROOM_UNIT_PATTERN}\b", lower, flags=re.IGNORECASE) or re.search(r"\b(?:standard|std\.?|superior|double|single|twin|family|junior|suite|room|rooms|apartment|villa|cottage|lodge|breakfast|brekafast|dinner)\b", lower))


def clean_hotel_name_from_source(row: dict) -> str:
    source, city = clean_space(row.get("details", "")), clean_space(row.get("city", ""))
    source = re.sub(r"\([^)]*(?:supplement|upgrade)[^)]*\)", "", source, flags=re.IGNORECASE)
    candidates = []
    prefixes = ("scandic", "radisson", "comfort", "quality", "clarion", "thon", "moxy", "grand", "hotel", "santa", "kakslauttanen")
    for part in [clean_space(item) for item in re.split(r"\s+-\s+|,|\|", source) if clean_space(item)]:
        cleaned = polish_hotel_name(_strip_city_and_star_prefix(part, city)); lower = cleaned.lower()
        if city and lower == city.lower(): continue
        if any(marker in lower for marker in ("check in", "check-in", "accommodation", "night stay", "breakfast", "brekafast", "dinner", "half board", "full board", "room only", "self catering", "self-catering", "included")): continue
        if re.fullmatch(r"\s*\d\s*[- ]?star\s*", lower): continue
        if re.search(r"\b\d+\s*(?:x\s*)?(?:night|ngiht|nite|nt)s?", lower):
            cleaned = re.sub(r"^\s*\d+\s*(?:x\s*)?(?:night|ngiht|nite|nt)'?s?\s*|\s*\d+\s*(?:x\s*)?(?:night|ngiht|nite|nt)'?s?\s*$", "", cleaned, flags=re.IGNORECASE).strip(" ,-:")
            lower = cleaned.lower()
            if not cleaned: continue
        if _looks_like_room_fragment(cleaned): continue
        if any(lower.startswith(f"hotel {brand}") for brand in ("scandic", "radisson", "comfort", "quality", "clarion", "thon", "moxy", "grand")): cleaned = cleaned[6:].strip()
        if lower.startswith(prefixes) or len(cleaned.split()) >= 2: candidates.append(cleaned)
    return polish_hotel_name(candidates[0]) if candidates else ""


def strip_city_and_star_prefix(value: str, city: str = "") -> str:
    return _strip_city_and_star_prefix(value, city)
