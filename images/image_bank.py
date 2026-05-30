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

def _candidate_external_image_bank_paths(root: Path) -> list[Path]:
    """Return optional external image-bank roots in priority order.

    Production-sized destination imagery can live outside the app repository,
    next to it, so the code repo stays lightweight. The default sibling layout
    is::

        itinerary_app/
          itinerary-creator-git/
          itinerary-image-bank/image_bank_full/

    An environment variable may override or add another bank location without
    changing code.
    """

    import os

    paths: list[Path] = []
    env_value = clean_space(os.environ.get("ITINERARY_IMAGE_BANK_FULL", ""))
    if env_value:
        paths.append(Path(env_value).expanduser())

    paths.append(root.parent / "itinerary-image-bank" / "image_bank_full")
    return paths


def _dedupe_existing_paths(paths: list[Path]) -> list[Path]:
    selected: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists() or not path.is_dir():
            continue
        try:
            key = str(path.resolve())
        except Exception:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        selected.append(path)
    return selected


def get_image_bank_paths(root=None):
    """Return image-bank paths in priority order.

    Destination-specific production imagery is scanned first when the sibling
    ``itinerary-image-bank`` repository is present. The in-repo banks remain as
    safe fallbacks for tests, clean zips and deployments that do not install
    the external image-bank repository.
    """
    root = Path(root) if root is not None else APP_ROOT
    external_banks = _candidate_external_image_bank_paths(root)
    full_bank = root / "image_bank_full"
    fallback_bank = root / "image_bank"
    paths = _dedupe_existing_paths([*external_banks, full_bank, fallback_bank])
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

