"""App-facing day image helpers.

Keeps image-bank path handling, per-day image overrides, upload helpers,
and the preview/PDF day-image marker out of app.py.
"""

from pathlib import Path
import base64
import html
import mimetypes
import re

from image_matcher import select_day_image, select_day_images, scan_image_bank
from text_polish import polish_title

APP_ROOT = Path(__file__).resolve().parents[1]


def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def esc(value):
    return html.escape(str(value or ""), quote=True)

CROP_FOCUS_OPTIONS = {
    "Sky / upper focus": "top",
    "Center focus": "center",
    "Lower focus": "bottom",
}

CROP_FOCUS_LABELS = {value: label for label, value in CROP_FOCUS_OPTIONS.items()}

CROP_FOCUS_OBJECT_POSITIONS = {
    "top": "center 22%",
    "center": "center center",
    "bottom": "center 78%",
}

def get_image_bank_path():
    return APP_ROOT / "image_bank"


def normalize_path_key(value):
    try:
        return str(Path(str(value or "")).resolve())
    except Exception:
        return str(value or "")


def slugify_filename(value):
    text = clean_space(value) or "Image"
    text = re.sub(r"[^A-Za-z0-9_ -]+", "", text)
    text = re.sub(r"[\s-]+", "_", text).strip("_")
    return text or "Image"


def infer_country_for_city(city):
    city_key = clean_space(city).lower()
    for candidate in scan_image_bank(get_image_bank_path()):
        if clean_space(candidate.city).lower() == city_key and candidate.country:
            return candidate.country
    return "Custom"


def image_to_data_uri(path):
    try:
        path = Path(path)
        if not path.exists() or not path.is_file():
            return ""
        mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


def get_day_image_overrides(output_edits=None):
    return (output_edits or {}).setdefault("day_images", {})


def normalize_crop_focus(value):
    value = str(value or "").strip().lower()
    if value in {"top", "upper", "sky", "aurora"}:
        return "top"
    if value in {"bottom", "lower"}:
        return "bottom"
    if value in {"center", "centre", "middle"}:
        return "center"
    return "top"


def get_day_image_choice(output_edits, day):
    day_images = get_day_image_overrides(output_edits)
    choice = day_images.setdefault(day, {"mode": "auto", "path": "", "crop_focus": "top"})
    choice.setdefault("mode", "auto")
    choice.setdefault("path", "")
    choice["crop_focus"] = normalize_crop_focus(choice.get("crop_focus", "top"))
    return choice


def get_day_image_crop_focus(output_edits, day):
    return normalize_crop_focus(get_day_image_choice(output_edits, day).get("crop_focus", "top"))


def day_image_match_from_path(day, path, reason="manual selection"):
    if not path:
        return None
    path_obj = Path(path)
    return {
        "day": day,
        "path": str(path_obj),
        "score": 999,
        "reason": reason,
        "city": "",
        "country": "",
        "filename": path_obj.stem,
        "themes": [],
        "seasons": [],
    }


def select_day_images_with_overrides(grouped_days, output_edits=None):
    """Apply day image review choices while preserving no-reuse behavior."""

    overrides = (output_edits or {}).get("day_images", {}) or {}
    selected = {}
    used_paths = set()

    # Manual and removed choices first, so automatic selections cannot reuse a
    # picture selected by the user on another day.
    for day, rows in (grouped_days or {}).items():
        choice = overrides.get(day, {}) or {}
        mode = choice.get("mode", "auto")
        manual_path = choice.get("path", "")

        if mode == "none":
            selected[day] = None
            continue

        if mode == "manual" and manual_path:
            resolved = Path(manual_path)
            if not resolved.is_absolute():
                resolved = (APP_ROOT / resolved).resolve()
            key = normalize_path_key(resolved)
            if resolved.exists() and key not in used_paths:
                selected[day] = day_image_match_from_path(day, resolved, reason="manual image selection")
                used_paths.add(key)
            else:
                selected[day] = None

    base_matches = select_day_images(grouped_days, get_image_bank_path(), used_paths=used_paths.copy())

    for day, rows in (grouped_days or {}).items():
        if day in selected:
            continue
        match = base_matches.get(day)
        if match:
            key = normalize_path_key(match.get("path", ""))
            if key in used_paths:
                match = None
            else:
                used_paths.add(key)
        selected[day] = match

    return selected


def list_city_image_options(city):
    city_key = clean_space(city).lower()
    options = []
    for candidate in scan_image_bank(get_image_bank_path()):
        if clean_space(candidate.city).lower() == city_key:
            options.append(Path(candidate.path))
    return sorted(options, key=lambda path: path.name.lower())


def save_uploaded_day_image(uploaded_file, city, season, label=""):
    if not uploaded_file:
        return ""
    city_name = polish_title(city) or "Destination"
    country = infer_country_for_city(city_name)
    season_name = season if season in {"Summer", "Winter"} else "Summer"
    stem_bits = [slugify_filename(city_name), season_name, slugify_filename(label or Path(uploaded_file.name).stem)]
    suffix = Path(uploaded_file.name).suffix.lower() or ".jpg"
    target_dir = get_image_bank_path() / slugify_filename(country) / slugify_filename(city_name)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / ("_".join([bit for bit in stem_bits if bit]) + suffix)

    counter = 2
    while target_path.exists():
        target_path = target_dir / ("_".join([bit for bit in stem_bits if bit]) + f"_{counter}" + suffix)
        counter += 1

    target_path.write_bytes(uploaded_file.getbuffer())
    return str(target_path)


def render_day_image_slot(day, rows, match=None, output_edits=None):
    """Return the day-image marker used by the preview and PDF exporter."""
    if match is None:
        match = select_day_image(day, rows, get_image_bank_path())
    if not match:
        return ""

    image_path = match.get("path", "")
    crop_focus = get_day_image_crop_focus(output_edits, day)
    object_position = CROP_FOCUS_OBJECT_POSITIONS.get(crop_focus, CROP_FOCUS_OBJECT_POSITIONS["top"])
    data_uri = image_to_data_uri(image_path)
    preview_img = ""
    if data_uri:
        preview_img = (
            f'<img class="day-image-preview-img" '
            f'style="object-position: {esc(object_position)};" '
            f'src="{esc(data_uri)}" alt="{esc(Path(image_path).stem)}" />'
        )

    return (
        f'<div class="day-image-slot" '
        f'data-image-path="{esc(image_path)}" '
        f'data-image-crop-focus="{esc(crop_focus)}" '
        f'data-image-score="{esc(match.get("score", ""))}" '
        f'data-image-reason="{esc(match.get("reason", ""))}">'
        f'{preview_img}'
        f'</div>'
    )
