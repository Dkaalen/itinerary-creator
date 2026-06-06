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
    # User workstation layout: app repo and full bank folder are siblings under
    # the same itinerary_app directory. Keep this before the local fallback so
    # destination imagery wins over the bundled Default bank.
    paths.append(root.parent / "image_bank_full")
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
    """Return whether the app may fetch the image-bank repo at runtime.

    The full destination image bank is a separate repository and is required for
    good Add Pictures results.  Local/sibling checkouts remain preferred, but a
    missing full bank should not silently degrade to the tiny bundled Default
    folder.  Runtime bootstrap is therefore on by default for normal app runs and
    can be disabled with ``ITINERARY_IMAGE_BANK_BOOTSTRAP=0``.  Tests stay offline
    unless they explicitly opt in.
    """

    value = clean_space(os.environ.get("ITINERARY_IMAGE_BANK_BOOTSTRAP", "")).lower()
    if value in {"0", "false", "no", "off", "disabled"}:
        return False
    if value in {"1", "true", "yes", "on", "enabled"}:
        return True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return True


def _ensure_runtime_image_bank(root: Path) -> Path | None:
    """Optionally clone the separate image-bank repo when explicitly enabled.

    Zip/deployment workflows should normally ship a populated image bank or set
    ``ITINERARY_IMAGE_BANK_FULL`` to a known local checkout.  Runtime cloning is
    used as the last-resort production fallback and can be disabled with
    ``ITINERARY_IMAGE_BANK_BOOTSTRAP=0``.
    """

    runtime_repo = root / RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank"
    runtime_bank = runtime_repo / "image_bank_full"
    if runtime_bank.exists() and any(runtime_bank.rglob("*.webp")):
        return runtime_bank

    if not _runtime_bootstrap_allowed():
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
    before local fallback banks. If no full bank is available, the app attempts a
    one-time runtime bootstrap from the image-bank GitHub repo before falling
    back to the tiny bundled Default bank. Set
    ``ITINERARY_IMAGE_BANK_BOOTSTRAP=0`` to disable that bootstrap.
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


def image_bank_status(root=None) -> dict:
    """Return operational image-bank status for diagnostics and quality gates."""

    root = Path(root) if root is not None else APP_ROOT
    paths = get_image_bank_paths(root)
    candidates = scan_image_bank(paths)
    destination_candidates = [candidate for candidate in candidates if clean_space(candidate.city).lower() not in {"default", "defoult"}]
    return {
        "paths": [str(path) for path in paths],
        "using_full_destination_bank": bool(destination_candidates),
        "destination_image_count": len(destination_candidates),
        "total_image_count": len(candidates),
        "runtime_bootstrap_allowed": _runtime_bootstrap_allowed(),
        "repo_url": IMAGE_BANK_REPO_URL,
    }


def infer_country_for_city(city, root=None):
    city_key = clean_space(city).lower()
    for candidate in scan_image_bank(get_image_bank_scan_paths(root)):
        if clean_space(candidate.city).lower() == city_key and candidate.country:
            return candidate.country
    return "Custom"
