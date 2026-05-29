"""App-facing day image helpers.

Keeps image-bank path handling, per-day image overrides, upload helpers,
and the preview/PDF day-image marker out of app.py.
"""

from pathlib import Path
from functools import lru_cache
import base64
import html
import mimetypes
import re

from image_matcher import (
    build_day_context,
    scan_image_bank,
    score_image_for_day,
    select_day_image,
    select_day_images,
)
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




@lru_cache(maxsize=256)
def _image_to_preview_data_uri_cached(path_text, max_size, quality, mtime):
    try:
        from io import BytesIO
        from PIL import Image

        path = Path(path_text)
        if not path.exists() or not path.is_file():
            return ""
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail(max_size, Image.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return ""


def image_to_preview_data_uri(path, max_size=(1100, 760), quality=74):
    """Return a browser-friendly preview data URI instead of the original image.

    The visual editor only needs a screen preview. Sending original local image
    files through Streamlit can create enormous component payloads when the
    image bank contains high-resolution photos. This helper keeps the editor
    responsive while the PDF exporter continues to use the original file path.
    """
    try:
        path = Path(path)
        if not path.exists() or not path.is_file():
            return ""
        cached = _image_to_preview_data_uri_cached(str(path.resolve()), tuple(max_size), int(quality), path.stat().st_mtime)
        if cached:
            return cached
    except Exception:
        pass

    # Fall back only for very small files. Large originals are exactly what
    # caused Streamlit message-size failures, so never blindly encode them.
    try:
        path = Path(path)
        if path.exists() and path.stat().st_size <= 750_000:
            return image_to_data_uri(path)
    except Exception:
        pass
    return ""


def image_to_option_preview_data_uri(path):
    """Return a tiny preview used only after choosing a replacement image."""
    return image_to_preview_data_uri(path, max_size=(420, 300), quality=60)


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


def list_replacement_image_options(city):
    """Return replacement pictures for a city, with Default images available."""
    city_key = clean_space(city).lower()
    city_options = []
    default_options = []
    seen = set()
    for candidate in scan_image_bank(get_image_bank_path()):
        path = Path(candidate.path)
        key = normalize_path_key(path)
        if key in seen:
            continue
        candidate_city = clean_space(candidate.city).lower()
        if city_key and candidate_city == city_key:
            city_options.append(path)
            seen.add(key)
        elif candidate_city == "default":
            default_options.append(path)
            seen.add(key)
    return sorted(city_options, key=lambda path: path.name.lower()) + sorted(default_options, key=lambda path: path.name.lower())


def list_replacement_image_options_for_rows(day, rows, limit=30):
    """Return lightweight, relevance-ranked replacement options for a day.

    The returned items intentionally contain no base64 image payload. The visual
    editor receives labels and paths only, preventing replacement lists from
    sending the full image bank to the browser.
    """
    candidates = scan_image_bank(get_image_bank_path())
    if not candidates:
        return []
    context = build_day_context(day, rows or [])
    scored = []
    seen = set()
    for candidate in candidates:
        path = Path(candidate.path)
        key = normalize_path_key(path)
        if key in seen:
            continue
        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue
        scored.append((score, candidate.filename.lower(), candidate, reasons))
        seen.add(key)
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    options = []
    for score, _filename, candidate, reasons in scored[:limit]:
        path = Path(candidate.path)
        options.append({
            "path": str(path),
            "name": path.name,
            "score": score,
            "reason": "; ".join(reasons or []),
            "themes": list(candidate.themes),
            "seasons": list(candidate.seasons),
            "city": candidate.city,
        })
    return options


def get_image_preview_for_path(path, option=False):
    if not path:
        return ""
    return image_to_option_preview_data_uri(path) if option else image_to_preview_data_uri(path)


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




def save_data_uri_day_image(data_uri, filename, city, season='Summer', label=''):
    """Save a visual-editor uploaded data URI into the local image bank."""
    if not data_uri or not str(data_uri).startswith('data:'):
        return ''
    try:
        header, encoded = str(data_uri).split(',', 1)
        raw = base64.b64decode(encoded)
    except Exception:
        return ''

    class _UploadedBytes:
        def __init__(self, name, data):
            self.name = name or 'uploaded_image.jpg'
            self._data = data
        def getbuffer(self):
            return self._data

    return save_uploaded_day_image(_UploadedBytes(filename, raw), city, season, label)


def render_day_image_slot(day, rows, match=None, output_edits=None):
    """Return the day-image marker used by the preview and PDF exporter."""
    if match is None:
        match = select_day_image(day, rows, get_image_bank_path())
    if not match:
        return ""

    image_path = match.get("path", "")
    crop_focus = get_day_image_crop_focus(output_edits, day)
    object_position = CROP_FOCUS_OBJECT_POSITIONS.get(crop_focus, CROP_FOCUS_OBJECT_POSITIONS["top"])
    data_uri = image_to_preview_data_uri(image_path)
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
