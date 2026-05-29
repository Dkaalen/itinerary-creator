"""Image-bank path and filename helpers."""

from pathlib import Path
import html
import re

from image_matcher import scan_image_bank

APP_ROOT = Path(__file__).resolve().parents[1]

def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()

def esc(value):
    return html.escape(str(value or ""), quote=True)

def get_image_bank_paths(root=None):
    """Return image-bank paths in priority order.

    ``image_bank_full`` is the production/main bank when present.
    ``image_bank`` remains the small fallback bank for local clean zips and
    deployments that do not include the full bank.
    """
    root = Path(root) if root is not None else APP_ROOT
    full_bank = root / "image_bank_full"
    fallback_bank = root / "image_bank"
    paths = [path for path in (full_bank, fallback_bank) if path.exists()]
    return paths or [fallback_bank]

def get_image_bank_path(root=None):
    """Return the primary writable image-bank path."""
    return get_image_bank_paths(root)[0]

def get_image_bank_scan_paths(root=None):
    """Return all image-bank paths used for matching and replacement scans."""
    return get_image_bank_paths(root)

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

def infer_country_for_city(city, root=None):
    city_key = clean_space(city).lower()
    for candidate in scan_image_bank(get_image_bank_scan_paths(root)):
        if clean_space(candidate.city).lower() == city_key and candidate.country:
            return candidate.country
    return "Custom"

