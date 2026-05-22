"""
image_matcher.py

Image-bank matching for itinerary day imagery.

Expected folder shape:
    image_bank/
        Norway/
            Oslo/
                Oslo_Summer_Opera_House.jpg
                Oslo_Winter_Northern_Lights.jpg

The matcher is intentionally conservative: if there is no image for the day's
own destination/city, it returns None. A missing image is better than a wrong
image in a premium itinerary.
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
    """Infer the itinerary season from day dates when available.

    The image bank supports two broad naming seasons: Summer and Winter. The
    inference is deliberately simple and only returns a season when a month can
    be read from the row data. If no date exists, matching remains season-neutral.
    """
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
        "season": infer_season_from_rows(rows),
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

    # Hard destination rule: no image for this destination means no image.
    if not day_city_variants or not (candidate_city_variants & day_city_variants):
        return 0, ["no destination match"]

    score += 60
    reasons.append("city folder match")

    if filename_city_variants & day_city_variants:
        score += 20
        reasons.append("city filename match")

    theme_matches = candidate_themes & day_themes
    if theme_matches:
        score += 18 * len(theme_matches)
        reasons.append("theme match: " + ", ".join(sorted(theme_matches)))

    day_season = normalize_keyword(day_context.get("season", ""))
    candidate_seasons = set(candidate.seasons)
    if day_season and day_season in candidate_seasons:
        score += 12
        reasons.append(f"season match: {day_season}")

    token_matches = (candidate_tokens & day_tokens) - day_city_variants - set(SEASON_ALIASES)
    if token_matches:
        score += min(20, 4 * len(token_matches))
        reasons.append("keyword match: " + ", ".join(sorted(list(token_matches))[:5]))

    return score, reasons


def _season_available_for_context(candidates: list[ImageCandidate], context: dict) -> bool:
    day_season = normalize_keyword(context.get("season", ""))
    if not day_season:
        return False

    day_city_variants = set(context.get("city_variants", set()))
    for candidate in candidates:
        if day_season not in set(candidate.seasons):
            continue
        candidate_city_variants = city_variants(candidate.city)
        if candidate_city_variants & day_city_variants:
            return True
    return False


def _select_best_candidate_for_context(
    day: str,
    context: dict,
    candidates: list[ImageCandidate],
    used_paths: set[str] | None = None,
) -> dict | None:
    used_paths = used_paths or set()
    best = None
    require_matching_season = _season_available_for_context(candidates, context)
    day_season = normalize_keyword(context.get("season", ""))

    for candidate in candidates:
        normalized_path = str(Path(candidate.path).resolve())
        if normalized_path in used_paths:
            continue
        if require_matching_season and day_season not in set(candidate.seasons):
            continue

        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue
        payload = {
            "day": day,
            "path": candidate.path,
            "score": score,
            "reason": "; ".join(reasons) if reasons else "destination match",
            "city": candidate.city,
            "country": candidate.country,
            "filename": candidate.filename,
            "themes": list(candidate.themes),
            "seasons": list(candidate.seasons),
        }
        if best is None or (payload["score"], payload["filename"]) > (best["score"], best["filename"]):
            best = payload
    return best


def select_day_image(day: str, rows: list[dict], image_bank_path: Path | str = "image_bank") -> dict | None:
    candidates = scan_image_bank(image_bank_path)
    if not candidates:
        return None
    context = build_day_context(day, rows)
    return _select_best_candidate_for_context(day, context, candidates)


def select_day_images(grouped_days: dict, image_bank_path: Path | str = "image_bank") -> dict:
    """Select at most one non-reused image for each day in itinerary order."""
    candidates = scan_image_bank(image_bank_path)
    if not candidates:
        return {day: None for day in (grouped_days or {})}

    matches = {}
    used_paths: set[str] = set()
    for day, rows in (grouped_days or {}).items():
        context = build_day_context(day, rows)
        match = _select_best_candidate_for_context(day, context, candidates, used_paths)
        matches[day] = match
        if match:
            used_paths.add(str(Path(match["path"]).resolve()))
    return matches


def format_match_for_debug(match: dict | None) -> str:
    if not match:
        return "No suitable image found"
    return f"{match['path']} — score {match['score']} ({match['reason']})"
