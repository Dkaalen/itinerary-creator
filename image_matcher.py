"""
image_matcher.py

Image-bank matching for itinerary day imagery.

Expected folder shape:
    image_bank/
        Default/
            Default_Summer_Fjord_View_01.jpg
            Default_Winter_Northern_Lights_01.jpg
        Norway/
            Oslo/
                Oslo_Summer_Opera_House.jpg
                Oslo_Winter_Northern_Lights.jpg
        Finland/
        Sweden/
        Denmark/
        Iceland/

Matching is destination-first. A destination/city image always wins when it is
available. If a destination is missing, the root-level Default folder provides
a controlled fallback pool, scored against day content so generic images still
feel semi-relevant.
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
    "fjord": {"fjord", "fjords", "kvaloya", "kvaløya", "sommaroy", "sommarøy", "cruise", "boat", "lake", "waterfall"},
    "city": {"city", "center", "centre", "street", "streets", "walking", "sightseeing", "landmarks", "arrival", "departure", "skyline", "buildings"},
    "waterfront": {"waterfront", "harbour", "harbor", "brygge", "aker", "bjorvika", "bjørvika", "opera", "skyline", "coast", "coastal"},
    "mountain": {"mountain", "mountains", "viewpoint", "view", "hike", "hiking", "valley", "road", "scenic", "landscape", "forest"},
    "winter": {"winter", "snow", "snowy", "ice", "icy", "arctic", "frozen"},
    "old town": {"old", "town", "oldtown", "historic", "medieval"},
    "santa": {"santa", "claus", "christmas", "arctic", "circle"},
    "wildlife": {"wildlife", "ranua", "animals", "zoo", "reindeer"},
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
    # Standard destination folders are Country/City/Image. A root-level Default
    # folder is special: Default/Image. Also support scanning the Default folder
    # itself directly, because the app uses that as a hard fallback repair path
    # when an external image-bank setting is missing or empty.
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


def _coerce_image_bank_paths(image_bank_path: Path | str | list | tuple | set = "image_bank") -> list[Path]:
    if isinstance(image_bank_path, (list, tuple, set)):
        values = list(image_bank_path)
    else:
        values = [image_bank_path]

    paths: list[Path] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        path = Path(value).expanduser()
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def scan_image_bank(image_bank_path: Path | str | list | tuple | set = "image_bank") -> list[ImageCandidate]:
    candidates = []
    seen_files: set[str] = set()
    for base in _coerce_image_bank_paths(image_bank_path):
        if not base.exists() or not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            key = str(path.resolve())
            if key in seen_files:
                continue
            seen_files.add(key)
            candidates.append(extract_image_metadata(path, base))
    return candidates


def get_image_bank_diagnostics(image_bank_path: Path | str | list | tuple | set = "image_bank") -> dict:
    """Return lightweight scan diagnostics for the app sidebar/debug panels.

    This intentionally reuses scan_image_bank rather than maintaining a second
    scanner. The counts make it obvious when the root Default folder is not
    being picked up, which is the most important failure mode for missing
    destination fallback imagery.
    """
    paths = _coerce_image_bank_paths(image_bank_path)
    candidates = scan_image_bank(paths)
    default_images = [candidate for candidate in candidates if _is_global_default_candidate(candidate)]
    destination_images = [candidate for candidate in candidates if not _is_global_default_candidate(candidate)]
    by_city: dict[str, int] = {}
    by_country: dict[str, int] = {}
    for candidate in candidates:
        city_key = candidate.city or "Default"
        country_key = candidate.country or "Global"
        by_city[city_key] = by_city.get(city_key, 0) + 1
        by_country[country_key] = by_country.get(country_key, 0) + 1

    return {
        "paths": [str(path) for path in paths],
        "existing_paths": [str(path) for path in paths if path.exists() and path.is_dir()],
        "total_images": len(candidates),
        "default_images": len(default_images),
        "destination_images": len(destination_images),
        "by_city": dict(sorted(by_city.items(), key=lambda item: item[0].lower())),
        "by_country": dict(sorted(by_country.items(), key=lambda item: item[0].lower())),
    }


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


def _is_global_default_candidate(candidate: ImageCandidate) -> bool:
    return normalize_keyword(candidate.city) in {"default", "defoult"}


def _candidate_destination_matches(candidate: ImageCandidate, day_context: dict) -> bool:
    day_city_variants = set(day_context.get("city_variants", set()))
    if not day_city_variants:
        return False
    candidate_city_variants = city_variants(candidate.city)
    return bool(candidate_city_variants & day_city_variants)


def _score_default_candidate(candidate: ImageCandidate, day_context: dict) -> tuple[int, list[str]]:
    score = 8
    reasons = ["global default fallback"]
    candidate_tokens = set(candidate.tokens)
    candidate_themes = set(candidate.themes)
    day_tokens = set(day_context.get("tokens", set()))
    day_themes = set(day_context.get("themes", set()))

    theme_matches = candidate_themes & day_themes
    if theme_matches:
        score += 20 * len(theme_matches)
        reasons.append("fallback theme match: " + ", ".join(sorted(theme_matches)))

    day_season = normalize_keyword(day_context.get("season", ""))
    candidate_seasons = set(candidate.seasons)
    if day_season and day_season in candidate_seasons:
        score += 8
        reasons.append(f"fallback season match: {day_season}")

    token_matches = (candidate_tokens & day_tokens) - {"default", "summer", "winter", "unknown"}
    if token_matches:
        score += min(16, 3 * len(token_matches))
        reasons.append("fallback keyword match: " + ", ".join(sorted(list(token_matches))[:5]))

    # Keep generic defaults safely below real destination matches, but make
    # obviously relevant defaults rank above unrelated generic defaults.
    return min(score, 55), reasons


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

    if _is_global_default_candidate(candidate):
        return _score_default_candidate(candidate, day_context)

    # Destination-specific rule: non-default images must match the day's city.
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

    for candidate in candidates:
        if day_season not in set(candidate.seasons):
            continue
        if _candidate_destination_matches(candidate, context) or _is_global_default_candidate(candidate):
            return True
    return False


def _candidate_to_payload(day: str, candidate: ImageCandidate, score: int, reasons: list[str]) -> dict:
    return {
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


def _select_best_candidate_for_context(
    day: str,
    context: dict,
    candidates: list[ImageCandidate],
    used_paths: set[str] | None = None,
    *,
    allow_default_repair: bool = True,
) -> dict | None:
    used_paths = used_paths or set()
    best = None
    require_matching_season = _season_available_for_context(candidates, context)
    day_season = normalize_keyword(context.get("season", ""))

    skipped_default_candidates: list[ImageCandidate] = []

    for candidate in candidates:
        normalized_path = str(Path(candidate.path).resolve())
        if normalized_path in used_paths:
            continue
        if require_matching_season and day_season not in set(candidate.seasons):
            if _is_global_default_candidate(candidate):
                skipped_default_candidates.append(candidate)
            continue

        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue
        payload = _candidate_to_payload(day, candidate, score, reasons)
        if best is None or (payload["score"], payload["filename"]) > (best["score"], best["filename"]):
            best = payload

    if best or not allow_default_repair:
        return best

    # Defensive fallback: a root-level Default image should be used whenever a
    # destination image is unavailable. This branch intentionally ignores the
    # broad season filter because a generic image is still better than a blank
    # page, and users can manually replace it in the visual editor.
    default_candidates = [
        candidate for candidate in candidates
        if _is_global_default_candidate(candidate)
        and str(Path(candidate.path).resolve()) not in used_paths
    ]
    if not default_candidates:
        return None

    default_best = None
    for candidate in default_candidates:
        score, reasons = _score_default_candidate(candidate, context)
        score = max(1, score)
        reasons = list(reasons or []) + ["defensive default repair"]
        payload = _candidate_to_payload(day, candidate, score, reasons)
        if default_best is None or (payload["score"], payload["filename"]) > (default_best["score"], default_best["filename"]):
            default_best = payload
    return default_best


def select_day_image(day: str, rows: list[dict], image_bank_path: Path | str = "image_bank") -> dict | None:
    candidates = scan_image_bank(image_bank_path)
    if not candidates:
        return None
    context = build_day_context(day, rows)
    return _select_best_candidate_for_context(day, context, candidates)


def select_day_images(
    grouped_days: dict,
    image_bank_path: Path | str = "image_bank",
    used_paths: set[str] | None = None,
) -> dict:
    """Select at most one non-reused image for each day in itinerary order."""
    candidates = scan_image_bank(image_bank_path)
    if not candidates:
        return {day: None for day in (grouped_days or {})}

    matches = {}
    used_paths = {str(Path(path).resolve()) for path in (used_paths or set())}
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
