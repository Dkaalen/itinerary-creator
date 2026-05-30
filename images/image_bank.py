"""Image-bank path and filename helpers."""

from pathlib import Path
import html
import re

from image_matcher import scan_image_bank

APP_ROOT = Path(__file__).resolve().parents[1]
IMAGE_BANK_REPO_URL = "https://github.com/Dkaalen/itinerary-image-bank.git"
IMAGE_BANK_BOOTSTRAP_ENV = "ITINERARY_IMAGE_BANK_BOOTSTRAP"

def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()

def esc(value):
    return html.escape(str(value or ""), quote=True)


def _path_has_full_bank(path: Path) -> bool:
    return path.exists() and path.is_dir() and any(path.rglob("*.webp"))


def _should_bootstrap_image_bank(root: Path) -> bool:
    """Return whether runtime cloning should be attempted when the bank is missing."""

    import os

    setting = clean_space(os.environ.get(IMAGE_BANK_BOOTSTRAP_ENV, "")).lower()
    if setting in {"0", "false", "no", "off"}:
        return False
    if setting in {"1", "true", "yes", "on"}:
        return True

    # Never auto-clone during pytest unless explicitly enabled above. Some
    # regression tests use the real repository root, where .gitmodules may be
    # present, and network access would make those tests slow or flaky.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False

    # Auto-enable only for app checkouts that clearly know about the external
    # bank. This prevents unit tests or unrelated imports from unexpectedly
    # trying network access.
    return (root / ".gitmodules").exists() or (root / "itinerary-image-bank" / "README_SUBMODULE_PLACEHOLDER.txt").exists()


def _runtime_clone_targets(root: Path) -> list[Path]:
    """Return writable locations where the image-bank repo may be cloned."""

    import tempfile

    candidates = [root / ".runtime_image_bank" / "itinerary-image-bank"]
    temp_root = Path(tempfile.gettempdir()) / "itinerary-image-bank-runtime"
    candidates.append(temp_root / "itinerary-image-bank")
    return candidates


def _try_bootstrap_image_bank(root: Path) -> Path | None:
    """Best-effort runtime install for deployments that do not clone submodules.

    Some deployment and ZIP workflows include ``.gitmodules`` but do not
    populate the submodule directory. In that case the app used to fall back to
    the small default bank. This helper clones the image-bank repository into a
    runtime cache so destination-specific images can still be used.
    """

    if not _should_bootstrap_image_bank(root):
        return None

    import subprocess

    for repo_dir in _runtime_clone_targets(root):
        full_bank = repo_dir / "image_bank_full"
        if _path_has_full_bank(full_bank):
            return full_bank

        # Avoid cloning into a partially populated or non-empty folder. This is
        # especially important when ``itinerary-image-bank`` is only a placeholder
        # directory in a ZIP export.
        if repo_dir.exists() and any(repo_dir.iterdir()):
            continue

        try:
            repo_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--depth", "1", IMAGE_BANK_REPO_URL, str(repo_dir)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=180,
            )
        except Exception:
            continue

        if _path_has_full_bank(full_bank):
            return full_bank
    return None


def _candidate_external_image_bank_paths(root: Path) -> list[Path]:
    """Return optional external image-bank roots in priority order.

    Production-sized destination imagery can be installed as a Git submodule
    inside this repository, as a sibling repository next to it, or as a runtime
    cache cloned from GitHub when deployment does not populate submodules.
    """

    import os

    paths: list[Path] = []
    env_value = clean_space(os.environ.get("ITINERARY_IMAGE_BANK_FULL", ""))
    if env_value:
        paths.append(Path(env_value).expanduser())

    # Git submodule layout: the image-bank repo is cloned inside the app repo.
    paths.append(root / "itinerary-image-bank" / "image_bank_full")
    # Local sibling layout: the image-bank repo sits beside the app repo.
    paths.append(root.parent / "itinerary-image-bank" / "image_bank_full")

    bootstrapped = _try_bootstrap_image_bank(root)
    if bootstrapped:
        paths.append(bootstrapped)
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

    Destination-specific production imagery is scanned first when the
    ``itinerary-image-bank`` repository is present as a submodule, sibling, or
    runtime cache. The in-repo banks remain as safe fallbacks for tests, clean
    zips and deployments that cannot install the external image-bank repository.
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
