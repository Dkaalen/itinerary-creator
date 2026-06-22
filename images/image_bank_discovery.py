"""Side-effect-free image-bank path discovery helpers."""

from pathlib import Path
import re

import diagnostics
from PIL import Image, UnidentifiedImageError

from images.remote_distribution import active_distribution_bank
from images.scanner import coerce_image_bank_paths
from images.image_bank_settings import (
    APP_ROOT,
    RUNTIME_IMAGE_BANK_DIR,
    SUPPORTED_IMAGE_EXTENSIONS,
    clean_space,
)


def candidate_external_image_bank_paths(root: Path) -> list[Path]:
    """Return external image-bank roots in priority order."""

    paths: list[Path] = []
    env_value = clean_space(__import__("os").environ.get("ITINERARY_IMAGE_BANK_FULL", ""))
    if env_value:
        paths.append(Path(env_value).expanduser())

    active_distribution = active_distribution_bank(root)
    if active_distribution is not None:
        paths.append(active_distribution)

    paths.append(root / "itinerary-image-bank" / "image_bank_full")
    paths.append(root.parent / "itinerary-image-bank" / "image_bank_full")
    paths.append(root.parent / "image_bank_full")
    paths.append(root / RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank" / "image_bank_full")
    return paths


def dedupe_existing_paths(paths: list[Path]) -> list[Path]:
    selected: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists() or not path.is_dir():
            continue
        try:
            key = str(path.resolve())
        except OSError as error:
            diagnostics.warn_exception("image_bank_path", "Could not resolve image-bank path.", error, str(path), source="images.image_bank")
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        selected.append(path)
    return selected


def looks_like_unpopulated_submodule(root: Path) -> bool:
    submodule_dir = root / "itinerary-image-bank"
    if not submodule_dir.exists():
        return False
    full_bank = submodule_dir / "image_bank_full"
    if full_bank.exists() and any(full_bank.rglob("*.webp")):
        return False
    return True


def runtime_bank_paths(root: Path) -> tuple[Path, Path]:
    runtime_repo = root / RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank"
    return runtime_repo, runtime_repo / "image_bank_full"


def valid_image_bank(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any(candidate.is_file() and candidate.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS for candidate in path.rglob("*"))


def valid_persistent_cache(path: Path) -> bool:
    """Require at least one structurally readable image before trusting a cache."""

    if not valid_image_bank(path):
        return False
    for candidate in path.rglob("*"):
        if not candidate.is_file() or candidate.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            continue
        try:
            with Image.open(candidate) as image:
                image.verify()
            return True
        except (OSError, SyntaxError, UnidentifiedImageError):
            continue
    return False


def get_image_bank_paths(root=None):
    """Return image-bank paths in priority order without side effects."""

    root = Path(root) if root is not None else APP_ROOT
    external_banks = candidate_external_image_bank_paths(root)
    full_bank = root / "image_bank_full"
    fallback_bank = root / "image_bank"
    paths = dedupe_existing_paths([*external_banks, full_bank, fallback_bank])
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
    except OSError as error:
        diagnostics.warn_exception("image_bank_path", "Could not normalize image path.", error, str(value or ""), source="images.image_bank")
        return str(value or "")


def slugify_filename(value):
    text = clean_space(value) or "Image"
    text = re.sub(r"[^A-Za-z0-9_ -]+", "", text)
    text = re.sub(r"[\s-]+", "_", text).strip("_")
    return text or "Image"


def is_default_city(value: str) -> bool:
    return clean_space(value).lower() in {"default", "defoult"}


def coerce_and_dedupe_paths(paths):
    return dedupe_existing_paths(coerce_image_bank_paths(paths))
