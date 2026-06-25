"""Configuration and cache paths for remote image-bank distribution."""

from __future__ import annotations

from pathlib import Path
import json
import os
import unicodedata

DEFAULT_MANIFEST_URL = (
    "https://github.com/Dkaalen/itinerary-image-bank/releases/download/"
    "image-bank-distribution/manifest.json"
)
DISTRIBUTION_DIR_NAME = "distribution"
ACTIVE_MANIFEST_NAME = "active.json"
MANIFEST_CACHE_NAME = "manifest.json"
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})
IMAGE_EXTENSIONS = frozenset({".webp", ".jpg", ".jpeg", ".png", ".avif"})
MAX_MANIFEST_BYTES = 25 * 1024 * 1024
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


def image_bank_manifest_url() -> str:
    return str(os.environ.get("ITINERARY_IMAGE_BANK_MANIFEST_URL", "") or DEFAULT_MANIFEST_URL).strip()


def normalise_lookup(value: str) -> str:
    text = str(value or "").strip().casefold()
    text = text.translate(str.maketrans({
        "ø": "o", "å": "a", "æ": "ae", "ð": "d", "þ": "th", "ł": "l",
    }))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join("".join(char if char.isalnum() else " " for char in text).split())


def safe_float_env(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def safe_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def manifest_ttl_seconds() -> float:
    return safe_float_env("ITINERARY_IMAGE_BANK_MANIFEST_TTL_SECONDS", 300.0, 0.0, 86400.0)


def network_timeout_seconds() -> float:
    return safe_float_env("ITINERARY_IMAGE_BANK_NETWORK_TIMEOUT_SECONDS", 25.0, 3.0, 180.0)


def lock_timeout_seconds() -> float:
    return safe_float_env("ITINERARY_IMAGE_BANK_LOCK_TIMEOUT_SECONDS", 120.0, 5.0, 600.0)


def download_workers() -> int:
    return safe_int_env("ITINERARY_IMAGE_BANK_DOWNLOAD_WORKERS", 4, 1, 8)


def distribution_root(app_root: Path) -> Path:
    override = str(os.environ.get("ITINERARY_IMAGE_BANK_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override).expanduser() / DISTRIBUTION_DIR_NAME
    return app_root / ".runtime_image_bank" / DISTRIBUTION_DIR_NAME


def active_distribution_bank(app_root: Path) -> Path | None:
    root = distribution_root(app_root)
    active_path = root / ACTIVE_MANIFEST_NAME
    try:
        payload = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    bank_version = str(payload.get("bank_version") or "").strip()
    if not bank_version:
        return None
    bank = root / "versions" / bank_version / "image_bank_full"
    return bank if bank.is_dir() else None
