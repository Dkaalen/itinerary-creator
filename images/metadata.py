"""Image metadata parsing and keyword helpers for itinerary image matching."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

CITY_ALIASES = {
    "tromso": {"tromso", "tromsø"},
    "tromsø": {"tromso", "tromsø"},
    "oslo": {"oslo"},
    "bergen": {"bergen"},
    "helsinki": {"helsinki"},
    "rovaniemi": {"rovaniemi"},
    "kakslauttanen": {"kakslauttanen", "kakslauttenen"},
    "kakslauttenen": {"kakslauttanen", "kakslauttenen"},
    "ivalo": {"ivalo"},
    "tallinn": {"tallinn"},
    "copenhagen": {"copenhagen", "kobenhavn", "københavn"},
    "stockholm": {"stockholm"},
    "kiruna": {"kiruna"},
    "reykjavik": {"reykjavik", "reykjavík", "reykjavaik"},
    "reykjavík": {"reykjavik", "reykjavík", "reykjavaik"},
    "reykjavaik": {"reykjavik", "reykjavík", "reykjavaik"},
    "keflavik": {"keflavik", "keflavík"},
    "keflavík": {"keflavik", "keflavík"},
    "vik": {"vik", "vík", "vik i myrdal", "vikimyrdal"},
    "vík": {"vik", "vík", "vik i myrdal", "vikimyrdal"},
    "vik i myrdal": {"vik", "vík", "vik i myrdal", "vikimyrdal"},
    "hella": {"hella"},
    "oraefi": {"oraefi", "öræfi", "oraefi"},
    "öræfi": {"oraefi", "öræfi"},
    "blue lagoon": {"blue lagoon", "bluelagoon"},
    "sky lagoon": {"sky lagoon", "skylagoon"},
    "south coast": {"south coast", "southcoast"},
    "hofn": {"hofn", "höfn"},
    "höfn": {"hofn", "höfn"},
    "egilsstadir": {"egilsstadir", "egilsstaðir"},
    "egilsstaðir": {"egilsstadir", "egilsstaðir"},
    "akureyri": {"akureyri"},
    "husavik": {"husavik", "húsavík"},
    "húsavík": {"husavik", "húsavík"},
    "myvatn": {"myvatn", "mývatn"},
    "mývatn": {"myvatn", "mývatn"},
    "jokulsarlon": {"jokulsarlon", "jökulsárlón", "jokulsárlón"},
    "jökulsárlón": {"jokulsarlon", "jökulsárlón", "jokulsárlón"},
    "flam": {"flam", "flåm"},
    "flåm": {"flam", "flåm"},
    "alesund": {"alesund", "ålesund"},
    "ålesund": {"alesund", "ålesund"},
    "gallivare": {"gallivare", "gällivare"},
    "gällivare": {"gallivare", "gällivare"},
    "abisko": {"abisko"},
    "are": {"are", "åre"},
    "åre": {"are", "åre"},
}

THEME_ALIASES = {
    "northern lights": {"northern", "lights", "northernlights", "aurora", "basecamp", "chase", "hunt"},
    "fjord": {"fjord", "fjords", "kvaloya", "kvaløya", "sommaroy", "sommarøy", "cruise", "boat", "lake", "waterfall"},
    "ocean": {"ocean", "sea", "whale", "whales", "boat", "harbour", "harbor"},
    "lagoon": {"lagoon", "spa", "ritual", "wellness", "blue", "sky"},
    "glacier": {"glacier", "glaciers", "ice", "crampon", "crampons", "jokull", "jökull"},
    "black sand": {"black", "sand", "beach", "volcano", "atv", "quad"},
    "city": {"city", "center", "centre", "street", "streets", "walking", "walk", "sightseeing", "landmarks", "arrival", "departure", "skyline", "buildings", "urban", "architecture"},
    "waterfront": {"waterfront", "harbour", "harbor", "brygge", "aker", "bjorvika", "bjørvika", "opera", "skyline", "coast", "coastal"},
    "mountain": {"mountain", "mountains", "viewpoint", "view", "hike", "hiking", "valley", "scenic", "landscape", "forest", "nature"},
    "winter": {"winter", "snow", "snowy", "ice", "icy", "arctic", "frozen"},
    "old town": {"old", "town", "oldtown", "historic", "medieval"},
    "santa": {"santa", "claus", "christmas", "arctic", "circle"},
    "wildlife": {"wildlife", "ranua", "animals", "zoo", "reindeer", "husky", "huskies", "sled", "sledding"},
    "igloo": {"glass", "igloo", "kakslauttanen", "arctic", "resort"},
    "train": {"train", "rail", "railway", "station", "overnight", "santa", "express", "nutshell", "flam", "flåm"},
    "road journey": {"road", "route", "coach", "bus", "panorama", "drive", "driving", "vehicle"},
    "funicular": {"funicular", "floibanen", "fløibanen", "mountain", "view"},
}

SEASON_ALIASES = {
    "summer": {"summer"},
    "winter": {"winter"},
}

SUMMER_MONTHS = {4, 5, 6, 7, 8, 9, 10}
WINTER_MONTHS = {1, 2, 3, 11, 12}


@dataclass(frozen=True)
class ImageCandidate:
    path: str
    country: str
    city: str
    filename: str
    tokens: tuple[str, ...]
    themes: tuple[str, ...]
    seasons: tuple[str, ...]


def normalize_keyword(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("ø", "o").replace("æ", "ae").replace("å", "a")
    text = text.replace("ä", "a").replace("ö", "o").replace("ü", "u")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def tokenize(value: str) -> set[str]:
    text = normalize_keyword(value)
    if not text:
        return set()
    words = text.split()
    tokens = set(words)
    for index in range(len(words) - 1):
        tokens.add(words[index] + words[index + 1])
    return tokens


def city_variants(value: str) -> set[str]:
    key = normalize_keyword(value)
    if not key:
        return set()
    variants = {key}
    for original, aliases in CITY_ALIASES.items():
        normalized_original = normalize_keyword(original)
        normalized_aliases = {normalize_keyword(alias) for alias in aliases}
        if key == normalized_original or key in normalized_aliases:
            variants.add(normalized_original)
            variants.update(normalized_aliases)
    return {variant for variant in variants if variant}


def infer_themes(tokens: set[str]) -> set[str]:
    themes = set()
    for theme, aliases in THEME_ALIASES.items():
        normalized_aliases = {normalize_keyword(alias) for alias in aliases}
        if tokens & normalized_aliases:
            themes.add(theme)
    return themes


def infer_seasons(tokens: set[str]) -> set[str]:
    seasons = set()
    for season, aliases in SEASON_ALIASES.items():
        normalized_aliases = {normalize_keyword(alias) for alias in aliases}
        if tokens & normalized_aliases:
            seasons.add(season)
    return seasons


def infer_season_from_rows(rows: list[dict]) -> str:
    """Infer the itinerary season from day dates when available."""
    for row in rows or []:
        for key in ("date", "start_date", "from_date", "check_in", "checkin"):
            value = str(row.get(key, "") or "").strip()
            if not value:
                continue

            patterns = [
                r"\b\d{1,2}[./-](\d{1,2})[./-]\d{2,4}\b",
                r"\b\d{4}[./-](\d{1,2})[./-]\d{1,2}\b",
            ]
            for pattern in patterns:
                match = re.search(pattern, value)
                if not match:
                    continue
                try:
                    month = int(match.group(1))
                except Exception:
                    continue
                if month in SUMMER_MONTHS:
                    return "summer"
                if month in WINTER_MONTHS:
                    return "winter"
    return ""


def extract_image_metadata(image_path: Path, image_bank_path: Path | str) -> ImageCandidate:
    base = Path(image_bank_path)
    path = Path(image_path)
    try:
        relative = path.relative_to(base)
    except ValueError:
        relative = path

    parts = list(relative.parts)
    if normalize_keyword(base.name) in {"default", "defoult"}:
        country = ""
        city = "Default"
    elif len(parts) >= 2 and normalize_keyword(parts[0]) in {"default", "defoult"}:
        country = ""
        city = "Default"
    else:
        country = parts[0] if len(parts) >= 3 else ""
        city = parts[1] if len(parts) >= 3 else (parts[0] if len(parts) >= 2 else "")
    filename = path.stem
    token_source = " ".join([country, city, filename.replace("_", " ")])
    tokens = tokenize(token_source)
    themes = infer_themes(tokens)
    seasons = infer_seasons(tokens)

    return ImageCandidate(
        path=str(path),
        country=country,
        city=city,
        filename=filename,
        tokens=tuple(sorted(tokens)),
        themes=tuple(sorted(themes)),
        seasons=tuple(sorted(seasons)),
    )
