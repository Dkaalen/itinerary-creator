"""Cover background asset helpers."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from itinerary_generation.cover_background_selector import select_cover_background_key
from itinerary_generation.cover_season import get_cover_season, normalize_cover_season
from itinerary_generation.cover_theme_constants import (
    COVER_BACKGROUND_DIR,
    SEASON_LABELS,
    SEASON_SUBTITLES,
    SEASON_TEXT_COLORS,
    SEASON_TITLES,
)


def get_cover_background_path(season: str, parsed_rows=None) -> Path | None:
    key = normalize_cover_season(season)
    if key == "automatic":
        key = "summer"
    key = select_cover_background_key(key, parsed_rows)
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = COVER_BACKGROUND_DIR / f"{key}{ext}"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def image_to_data_uri(path: Path | None) -> str:
    if not path:
        return ""
    try:
        path = Path(path)
        if not path.exists() or not path.is_file():
            return ""
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""




COVER_IMAGE_KEYS = {"cover_image", "summary_image"}


def normalize_cover_crop_focus(value: str) -> str:
    text = str(value or "top").strip().lower()
    return text if text in {"top", "center", "bottom"} else "top"


def cover_focus_css_position(value: str) -> str:
    focus = normalize_cover_crop_focus(value)
    if focus == "bottom":
        return "center bottom"
    if focus == "center":
        return "center center"
    return "center top"


def _cover_image_key(key: str) -> str:
    return key if key in COVER_IMAGE_KEYS else "cover_image"


def _normalize_cover_image_mode(value: object, *, removed: object = False, path: object = "") -> str:
    if bool(removed):
        return "none"
    raw_text = "" if value is None else str(value).strip().lower()
    text = raw_text or "auto"
    if text in {"none", "removed", "remove", "deleted", "delete"}:
        return "none"
    if text == "manual" or (not raw_text and str(path or "").strip()):
        return "manual"
    return "auto"


def get_cover_image_choice(output_edits=None, key: str = "cover_image") -> dict:
    edits = output_edits if isinstance(output_edits, dict) else {}
    raw = edits.get(_cover_image_key(key))
    raw = raw if isinstance(raw, dict) else {}
    mode = _normalize_cover_image_mode(raw.get("mode"), removed=raw.get("removed", False), path=raw.get("path", ""))
    return {
        "mode": mode,
        "path": "" if mode == "none" else str(raw.get("path") or ""),
        "crop_focus": normalize_cover_crop_focus(raw.get("crop_focus") or "top"),
    }


def list_cover_background_options() -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for path in sorted(COVER_BACKGROUND_DIR.glob("*")):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        label = path.stem.replace("_", " ").replace("-", " ").title()
        options.append({"path": str(path), "name": label})
    return options


def resolve_cover_background(parsed_rows, output_edits=None, *, key: str = "cover_image", include_image_data: bool = True) -> dict:
    season = get_cover_season(parsed_rows, output_edits)
    auto_path = get_cover_background_path(season, parsed_rows)
    choice = get_cover_image_choice(output_edits, key)
    selected_path: Path | None = auto_path
    if choice["mode"] == "none":
        selected_path = None
    elif choice["mode"] == "manual" and choice.get("path"):
        manual = Path(choice["path"])
        if manual.exists() and manual.is_file():
            selected_path = manual
        else:
            selected_path = None
    return {
        "mode": choice["mode"],
        "path": str(selected_path) if selected_path else "",
        "name": selected_path.name if selected_path else "",
        "data_uri": image_to_data_uri(selected_path) if include_image_data else "",
        "auto_path": str(auto_path) if auto_path else "",
        "auto_name": auto_path.name if auto_path else "",
        "auto_data_uri": image_to_data_uri(auto_path) if include_image_data else "",
        "crop_focus": choice["crop_focus"],
        "options": list_cover_background_options(),
    }


def get_cover_theme(parsed_rows, output_edits=None, *, include_image_data: bool = True) -> dict:
    season = get_cover_season(parsed_rows, output_edits)
    background_key = select_cover_background_key(season, parsed_rows)
    cover_image = resolve_cover_background(parsed_rows, output_edits, key="cover_image", include_image_data=include_image_data)
    path = Path(cover_image.get("path")) if cover_image.get("path") else None
    colors = dict(SEASON_TEXT_COLORS.get(season, SEASON_TEXT_COLORS["summer"]))
    if "northern_lights" in background_key:
        colors = {"ink": "#f5f1e8", "muted": "#d8cfbe", "accent": "#ead7a2"}
    return {
        "season": season,
        "background_key": background_key,
        "season_label": SEASON_LABELS.get(season, "Summer"),
        "title": SEASON_TITLES.get(season, SEASON_TITLES["summer"]),
        "subtitle": SEASON_SUBTITLES.get(season, SEASON_SUBTITLES["summer"]),
        "background_path": str(path) if path else "",
        "background_data_uri": cover_image.get("data_uri", "") if include_image_data else "",
        "background_crop_focus": cover_image.get("crop_focus", "top"),
        "ink": colors["ink"],
        "muted": colors["muted"],
        "accent": colors["accent"],
    }
