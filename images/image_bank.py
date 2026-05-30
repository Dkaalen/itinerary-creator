"""Image-bank path and filename helpers."""

from pathlib import Path
import html
import os
import re
import shutil
import subprocess

from image_matcher import scan_image_bank

APP_ROOT = Path(__file__).resolve().parents[1]
IMAGE_BANK_REPO_URL = "https://github.com/Dkaalen/itinerary-image-bank.git"
RUNTIME_IMAGE_BANK_DIR = ".runtime_image_bank"


def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def esc(value):
    return html.escape(str(value or ""), quote=True)


def _candidate_external_image_bank_paths(root: Path) -> list[Path]:
    """Return external image-bank roots in priority order.

    The app and the large destination image bank live in separate GitHub repos.
    Depending on how the app is checked out, the image bank may be available as
    an in-repo submodule, as a sibling checkout, or via an environment override.
    """

    paths: list[Path] = []
    env_value = clean_space(os.environ.get("ITINERARY_IMAGE_BANK_FULL", ""))
    if env_value:
        paths.append(Path(env_value).expanduser())

    # GitHub/deployment submodule layout.
    paths.append(root / "itinerary-image-bank" / "image_bank_full")
    # Local sibling-repo layout.
    paths.append(root.parent / "itinerary-image-bank" / "image_bank_full")
    # Runtime bootstrap fallback for zip/deploy checkouts that do not populate
    # submodules. This path is populated lazily by _ensure_runtime_image_bank().
    paths.append(root / RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank" / "image_bank_full")
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


def _looks_like_unpopulated_submodule(root: Path) -> bool:
    submodule_dir = root / "itinerary-image-bank"
    if not submodule_dir.exists():
        return False
    full_bank = submodule_dir / "image_bank_full"
    if full_bank.exists() and any(full_bank.rglob("*.webp")):
        return False
    return True


def _runtime_bootstrap_allowed() -> bool:
    # Unit tests should never attempt a network clone. Real app runs keep the
    # default enabled so zip/submodule deployments can fetch the image bank.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    value = clean_space(os.environ.get("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")).lower()
    return value not in {"0", "false", "no", "off"}


def _ensure_runtime_image_bank(root: Path) -> Path | None:
    """Clone the separate image-bank repo when submodules are unavailable.

    Some zip/deployment workflows include only a placeholder submodule folder.
    In that case, the app would otherwise silently use generic Default images.
    This bootstrap keeps destination images available while still failing safely
    when git/network access is unavailable.
    """

    runtime_repo = root / RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank"
    runtime_bank = runtime_repo / "image_bank_full"
    if runtime_bank.exists() and any(runtime_bank.rglob("*.webp")):
        return runtime_bank

    if not _runtime_bootstrap_allowed():
        return None
    if not _looks_like_unpopulated_submodule(root) and not (root / ".gitmodules").exists():
        return None
    if shutil.which("git") is None:
        return None

    try:
        runtime_repo.parent.mkdir(parents=True, exist_ok=True)
        if runtime_repo.exists():
            subprocess.run(
                ["git", "-C", str(runtime_repo), "pull", "--ff-only"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )
        else:
            subprocess.run(
                ["git", "clone", "--depth", "1", IMAGE_BANK_REPO_URL, str(runtime_repo)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=180,
            )
    except Exception:
        return None

    if runtime_bank.exists() and any(runtime_bank.rglob("*.webp")):
        return runtime_bank
    return None


def get_image_bank_paths(root=None):
    """Return image-bank paths in priority order.

    Destination-specific imagery from the separate image-bank repo is scanned
    before local fallback banks. If a submodule placeholder is present but the
    actual files are missing, the app tries a one-time runtime clone before
    falling back to generic images.
    """
    root = Path(root) if root is not None else APP_ROOT
    external_banks = _candidate_external_image_bank_paths(root)
    full_bank = root / "image_bank_full"
    fallback_bank = root / "image_bank"
    paths = _dedupe_existing_paths([*external_banks, full_bank, fallback_bank])
    if not paths or paths[0] in {full_bank, fallback_bank}:
        runtime_bank = _ensure_runtime_image_bank(root)
        if runtime_bank:
            paths = _dedupe_existing_paths([runtime_bank, *external_banks, full_bank, fallback_bank])
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
