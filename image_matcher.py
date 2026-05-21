"""
image_matcher.py

Image-bank foundation for itinerary day imagery.

This module intentionally does not place images in the PDF yet. It only scans the
image bank and selects the best candidate for each day, so matching can be tested
and debugged before layout work begins.

Expected folder shape:
    image_bank/
        Norway/
            Oslo/
                Oslo_Opera_House.jpg
                Oslo_Parliament_City_Centre.jpg
"""

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
    "gallivare": {"gallivare", "gällivare"},
    "gällivare": {"gallivare", "gällivare"},
}

THEME_ALIASES = {
    "northern lights": {"northern", "lights", "northernlights", "aurora", "basecamp", "chase", "hunt"},
    "fjord": {"fjord", "fjords", "kvaloya", "kvaløya", "sommaroy", "sommarøy", "cruise", "boat"},
    "city": {"city", "center", "centre", "street", "streets", "walking", "sightseeing", "landmarks"},
    "waterfront": {"waterfront", "harbour", "harbor", "brygge", "aker", "bjorvika", "bjørvika", "opera", "skyline"},
    "old town": {"old", "town", "oldtown", "historic", "medieval"},
    "santa": {"santa", "claus", "christmas", "arctic", "circle"},
    "wildlife": {"wildlife", "ranua", "animals", "zoo"},
    "igloo": {"glass", "igloo", "kakslauttanen", "arctic", "resort"},
    "train": {"train", "rail", "railway", "nutshell", "flam", "flåm"},
    "funicular": {"funicular", "floibanen", "fløibanen", "mountain", "view"},
}


@dataclass(frozen=True)
class ImageCandidate:
    path: str
    country: str
    city: str
    filename: str
    tokens: tuple[str, ...]
    themes: tuple[str, ...]


def normalize_keyword(value: str) -> str:
    """Normalize text for matching while keeping Nordic place names matchable."""

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
    tokens = set(text.split())
    # Preserve simple joined forms for themes such as "old town" and "northern lights".
    words = text.split()
    for index in range(len(words) - 1):
        tokens.add(words[index] + words[index + 1])
    return tokens


def city_variants(value: str) -> set[str]:
    key = normalize_keyword(value)
    if not key:
        return set()
    variants = {key}
    for original, aliases in CITY_ALIASES.items():
        normalized_aliases = {normalize_keyword(alias) for alias in aliases}
        if key == normalize_keyword(original) or key in normalized_aliases:
            variants.update(normalized_aliases)
            variants.add(normalize_keyword(original))
    return {variant for variant in variants if variant}


def infer_themes(tokens: set[str]) -> set[str]:
    themes = set()
    for theme, aliases in THEME_ALIASES.items():
        normalized_aliases = {normalize_keyword(alias) for alias in aliases}
        if tokens & normalized_aliases:
            themes.add(theme)
    return themes


def extract_image_metadata(image_path: Path, image_bank_path: Path | str) -> ImageCandidate:
    base = Path(image_bank_path)
    path = Path(image_path)

    try:
        relative = path.relative_to(base)
    except ValueError:
        relative = path

    parts = list(relative.parts)
    country = parts[0] if len(parts) >= 3 else ""
    city = parts[1] if len(parts) >= 3 else (parts[0] if len(parts) >= 2 else "")
    filename = path.stem

    token_source = " ".join([country, city, filename.replace("_", " ")])
    tokens = tokenize(token_source)
    themes = infer_themes(tokens)

    return ImageCandidate(
        path=str(path),
        country=country,
        city=city,
        filename=filename,
        tokens=tuple(sorted(tokens)),
        themes=tuple(sorted(themes)),
    )


def scan_image_bank(image_bank_path: Path | str = "image_bank") -> list[ImageCandidate]:
    base = Path(image_bank_path)
    if not base.exists() or not base.is_dir():
        return []

    candidates = []
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            candidates.append(extract_image_metadata(path, base))

    return candidates


def build_day_context(day: str, rows: list[dict]) -> dict:
    city = ""
    parts = [day]

    for row in rows or []:
        if not city and str(row.get("city", "")).strip():
            city = str(row.get("city", "")).strip()

        parts.extend(
            [
                str(row.get("city", "") or ""),
                str(row.get("title", "") or ""),
                str(row.get("original_title", "") or ""),
                str(row.get("details", "") or ""),
                str(row.get("display_description", "") or ""),
                " ".join(row.get("includes", []) or []),
            ]
        )

    text = " ".join(parts)
    tokens = tokenize(text)
    themes = infer_themes(tokens)

    return {
        "day": day,
        "city": city,
        "city_variants": city_variants(city),
        "tokens": tokens,
        "themes": themes,
        "text": normalize_keyword(text),
    }


def score_image_for_day(candidate: ImageCandidate, day_context: dict) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    candidate_tokens = set(candidate.tokens)
    candidate_themes = set(candidate.themes)
    day_tokens = set(day_context.get("tokens", set()))
    day_themes = set(day_context.get("themes", set()))
    day_city_variants = set(day_context.get("city_variants", set()))

    candidate_city_variants = city_variants(candidate.city)
    filename_city_variants = city_variants(candidate.filename)

    if day_city_variants and candidate_city_variants & day_city_variants:
        score += 60
        reasons.append("city folder match")

    if day_city_variants and filename_city_variants & day_city_variants:
        score += 20
        reasons.append("city filename match")

    theme_matches = candidate_themes & day_themes
    if theme_matches:
        score += 18 * len(theme_matches)
        reasons.append("theme match: " + ", ".join(sorted(theme_matches)))

    token_matches = (candidate_tokens & day_tokens) - day_city_variants
    if token_matches:
        score += min(20, 4 * len(token_matches))
        reasons.append("keyword match: " + ", ".join(sorted(list(token_matches))[:5]))

    # Avoid wrong-city images beating weaker correct-city matches.
    if day_city_variants and candidate_city_variants and not (candidate_city_variants & day_city_variants):
        score -= 50
        reasons.append("different city penalty")

    return score, reasons


def select_day_image(day: str, rows: list[dict], image_bank_path: Path | str = "image_bank") -> dict | None:
    candidates = scan_image_bank(image_bank_path)
    if not candidates:
        return None

    context = build_day_context(day, rows)
    best = None

    for candidate in candidates:
        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue

        payload = {
            "day": day,
            "path": candidate.path,
            "score": score,
            "reason": "; ".join(reasons) if reasons else "keyword match",
            "city": candidate.city,
            "country": candidate.country,
            "filename": candidate.filename,
            "themes": list(candidate.themes),
        }

        if best is None or (payload["score"], payload["filename"]) > (best["score"], best["filename"]):
            best = payload

    return best


def select_day_images(grouped_days: dict, image_bank_path: Path | str = "image_bank") -> dict:
    return {
        day: select_day_image(day, rows, image_bank_path)
        for day, rows in (grouped_days or {}).items()
    }


def format_match_for_debug(match: dict | None) -> str:
    if not match:
        return "No suitable image found"
    return f"{match['path']} — score {match['score']} ({match['reason']})"
