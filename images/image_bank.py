"""Image-bank path and filename helpers."""

from pathlib import Path
import html
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile

import diagnostics

from images.scanner import coerce_image_bank_paths, scan_image_bank

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE_BANK_REPO_URL = "https://github.com/Dkaalen/itinerary-image-bank.git"
DEFAULT_IMAGE_BANK_REPO_BRANCH = "main"
RUNTIME_IMAGE_BANK_DIR = ".runtime_image_bank"


def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def image_bank_repo_url() -> str:
    return clean_space(os.environ.get("ITINERARY_IMAGE_BANK_REPO_URL", "")) or DEFAULT_IMAGE_BANK_REPO_URL


def image_bank_repo_branch() -> str:
    return clean_space(os.environ.get("ITINERARY_IMAGE_BANK_REPO_BRANCH", "")) or DEFAULT_IMAGE_BANK_REPO_BRANCH


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
    # submodules. This path is populated only by explicit ensure_runtime_image_bank().
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
        except OSError as error:
            diagnostics.warn_exception("image_bank_path", "Could not resolve image-bank path.", error, str(path), source="images.image_bank")
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


def _repo_zip_url() -> str:
    """Return the GitHub archive URL for the configured image-bank repo."""

    repo_url = image_bank_repo_url()
    branch = image_bank_repo_branch()
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    return repo_url.rstrip("/") + f"/archive/refs/heads/{branch}.zip"


def _runtime_bank_paths(root: Path) -> tuple[Path, Path]:
    runtime_repo = root / RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank"
    return runtime_repo, runtime_repo / "image_bank_full"


def _valid_image_bank(path: Path) -> bool:
    return path.exists() and path.is_dir() and any(path.rglob("*.webp"))


def _setup_status(ok: bool, code: str, message: str, *, path: Path | None = None, error: str = "", method: str = "") -> dict:
    payload = {
        "ok": bool(ok),
        "code": code,
        "message": message,
        "path": str(path or ""),
        "repo_url": image_bank_repo_url(),
        "branch": image_bank_repo_branch(),
        "zip_url": _repo_zip_url(),
        "bootstrap_allowed": _runtime_bootstrap_allowed(),
        "method": method,
        "error": error,
    }
    if not ok:
        diagnostics.warn("image_bank_setup", message, error, source="images.image_bank")
    return payload


def _fetch_image_bank_with_git(runtime_repo: Path, runtime_bank: Path) -> dict:
    if shutil.which("git") is None:
        return _setup_status(False, "git_missing", "git is not available; ZIP download fallback will be attempted.", method="git")

    command = ["git", "clone", "--depth", "1", "--branch", image_bank_repo_branch(), image_bank_repo_url(), str(runtime_repo)]
    if runtime_repo.exists() and (runtime_repo / ".git").exists():
        command = ["git", "-C", str(runtime_repo), "pull", "--ff-only"]

    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180 if "clone" in command else 60,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return _setup_status(
            False,
            "git_command_failed",
            "Git could not fetch the image bank; ZIP download fallback will be attempted.",
            error=f"{type(error).__name__}: {error}",
            method="git",
        )

    if result.returncode != 0:
        error_text = " ".join((result.stderr or result.stdout or "").split())[:600]
        return _setup_status(
            False,
            "git_returned_error",
            "Git could not fetch the image bank; ZIP download fallback will be attempted.",
            error=error_text,
            method="git",
        )

    if _valid_image_bank(runtime_bank):
        return _setup_status(True, "fetched_git", "Image bank connected from GitHub using git.", path=runtime_bank, method="git")

    return _setup_status(
        False,
        "image_bank_missing_after_git_fetch",
        "Git finished, but image_bank_full was not found; ZIP download fallback will be attempted.",
        method="git",
    )


def _find_extracted_image_bank(extract_root: Path) -> Path | None:
    direct = extract_root / "image_bank_full"
    if _valid_image_bank(direct):
        return direct
    for candidate in extract_root.rglob("image_bank_full"):
        if _valid_image_bank(candidate):
            return candidate
    return None


def _fetch_image_bank_with_zip(runtime_repo: Path, runtime_bank: Path) -> dict:
    zip_url = _repo_zip_url()
    try:
        runtime_repo.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return _setup_status(
            False,
            "runtime_dir_failed",
            "Could not create the runtime image-bank folder.",
            error=f"{type(error).__name__}: {error}",
            method="zip",
        )

    with tempfile.TemporaryDirectory(prefix="image-bank-zip-") as tmp_text:
        tmp = Path(tmp_text)
        zip_path = tmp / "image-bank.zip"
        extract_root = tmp / "extract"
        try:
            urllib.request.urlretrieve(zip_url, zip_path)
        except (OSError, urllib.error.URLError, ValueError) as error:
            return _setup_status(
                False,
                "zip_download_failed",
                "Could not download the image bank ZIP from GitHub.",
                error=f"{type(error).__name__}: {error}",
                method="zip",
            )

        try:
            extract_root.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_root)
        except (OSError, zipfile.BadZipFile, RuntimeError) as error:
            return _setup_status(
                False,
                "zip_extract_failed",
                "Could not extract the image bank ZIP from GitHub.",
                error=f"{type(error).__name__}: {error}",
                method="zip",
            )

        extracted_bank = _find_extracted_image_bank(extract_root)
        if extracted_bank is None:
            return _setup_status(
                False,
                "zip_missing_image_bank_full",
                "Downloaded ZIP did not contain image_bank_full with WebP images.",
                method="zip",
            )

        try:
            if runtime_repo.exists():
                shutil.rmtree(runtime_repo)
            runtime_repo.mkdir(parents=True, exist_ok=True)
            shutil.copytree(extracted_bank, runtime_bank)
        except OSError as error:
            return _setup_status(
                False,
                "zip_install_failed",
                "Downloaded image bank could not be installed into runtime storage.",
                error=f"{type(error).__name__}: {error}",
                method="zip",
            )

    if _valid_image_bank(runtime_bank):
        return _setup_status(True, "fetched_zip", "Image bank connected from GitHub using ZIP download.", path=runtime_bank, method="zip")

    return _setup_status(False, "zip_install_missing_after_copy", "ZIP image bank install finished, but image_bank_full is missing.", method="zip")


def ensure_runtime_image_bank_status(root: Path | str | None = None) -> dict:
    """Explicitly fetch/update the runtime image bank and return diagnostics.

    The image bank remains a separate repository.  This connector installs a
    runtime/cache copy of Dkaalen/itinerary-image-bank/image_bank_full when the
    deployed app cannot see a mounted local copy.  It tries git first, then a
    GitHub ZIP download fallback for environments where git is unavailable.
    """

    root = Path(root) if root is not None else APP_ROOT
    runtime_repo, runtime_bank = _runtime_bank_paths(root)

    if _valid_image_bank(runtime_bank):
        return _setup_status(True, "already_available", "Runtime image bank is already connected.", path=runtime_bank, method="existing")

    if not _runtime_bootstrap_allowed():
        return _setup_status(
            False,
            "bootstrap_disabled",
            "Runtime image-bank fetching is disabled. Set ITINERARY_IMAGE_BANK_FULL or enable ITINERARY_IMAGE_BANK_BOOTSTRAP.",
        )

    try:
        runtime_repo.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return _setup_status(
            False,
            "runtime_dir_failed",
            "Could not create the runtime image-bank folder.",
            error=f"{type(error).__name__}: {error}",
        )

    git_status = _fetch_image_bank_with_git(runtime_repo, runtime_bank)
    if git_status.get("ok"):
        return git_status

    zip_status = _fetch_image_bank_with_zip(runtime_repo, runtime_bank)
    if zip_status.get("ok"):
        zip_status["fallback_from"] = git_status.get("code")
        return zip_status

    zip_status["fallback_from"] = git_status.get("code")
    zip_status["git_error"] = git_status.get("error", "")
    return zip_status


def connect_remote_image_bank_if_missing(root: Path | str | None = None) -> dict:
    """Connect the separate remote image-bank repo when no full bank is visible.

    This is app-facing: it may perform network work, but only when called by an
    explicit workflow such as Picture Review or PDF export.  Path lookup remains
    side-effect free.
    """

    root = Path(root) if root is not None else APP_ROOT
    current = image_bank_status(root)
    if current.get("full_bank_found"):
        current["setup_status"] = _setup_status(True, "already_connected", "Full destination image bank is already connected.", path=Path(current.get("source_path") or ""), method="existing")
        return current

    setup = ensure_runtime_image_bank_status(root)
    updated = image_bank_status(root)
    updated["setup_status"] = setup
    return updated


def ensure_runtime_image_bank(root: Path | str | None = None) -> Path | None:
    """Compatibility wrapper returning only the fetched path when setup succeeds."""

    status = ensure_runtime_image_bank_status(root)
    return Path(status["path"]) if status.get("ok") and status.get("path") else None


def get_image_bank_paths(root=None):
    """Return image-bank paths in priority order without side effects.

    Path discovery must be deterministic.  It may include an already-populated
    runtime checkout, but it must not clone, pull, or otherwise mutate the file
    system.  Use :func:`ensure_runtime_image_bank` as an explicit setup step when
    a deployment needs to fetch the separate image-bank repository.
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
    except OSError as error:
        diagnostics.warn_exception("image_bank_path", "Could not normalize image path.", error, str(value or ""), source="images.image_bank")
        return str(value or "")


def slugify_filename(value):
    text = clean_space(value) or "Image"
    text = re.sub(r"[^A-Za-z0-9_ -]+", "", text)
    text = re.sub(r"[\s-]+", "_", text).strip("_")
    return text or "Image"


def _is_default_city(value: str) -> bool:
    return clean_space(value).lower() in {"default", "defoult"}


def image_bank_status_for_paths(paths) -> dict:
    """Return image-bank status for a concrete path list.

    This is used by quality gates that already know which paths were scanned.
    It deliberately performs no network or bootstrap work.
    """

    scan_paths = _dedupe_existing_paths(coerce_image_bank_paths(paths))
    candidates = scan_image_bank(scan_paths)
    destination_candidates = [candidate for candidate in candidates if not _is_default_city(candidate.city)]
    default_candidates = [candidate for candidate in candidates if _is_default_city(candidate.city)]

    destination_paths: list[str] = []
    for base in scan_paths:
        base_candidates = scan_image_bank([base])
        if any(not _is_default_city(candidate.city) for candidate in base_candidates):
            destination_paths.append(str(base))

    countries = sorted({clean_space(candidate.country) for candidate in destination_candidates if clean_space(candidate.country)})
    destinations = sorted({clean_space(candidate.city) for candidate in destination_candidates if clean_space(candidate.city)})
    full_bank_found = bool(destination_candidates)
    default_only = bool(default_candidates) and not full_bank_found
    missing_full_bank = not full_bank_found
    blocking_message = ""
    if missing_full_bank:
        blocking_message = (
            "Full destination image bank is missing. Add Pictures is currently using only the bundled Default bank; "
            "connect the separate Dkaalen/itinerary-image-bank repository before approving final pictures."
        )

    return {
        "paths": [str(path) for path in scan_paths],
        "existing_paths": [str(path) for path in scan_paths if path.exists() and path.is_dir()],
        "source_path": destination_paths[0] if destination_paths else "",
        "destination_source_paths": destination_paths,
        "repo_url": image_bank_repo_url(),
        "branch": image_bank_repo_branch(),
        "zip_url": _repo_zip_url(),
        "full_bank_found": full_bank_found,
        "using_full_destination_bank": full_bank_found,
        "missing_full_bank": missing_full_bank,
        "default_only": default_only,
        "is_default_only": default_only,
        "destination_image_count": len(destination_candidates),
        "default_image_count": len(default_candidates),
        "total_image_count": len(candidates),
        "countries_found": countries,
        "destinations_found": destinations,
        "runtime_bootstrap_allowed": _runtime_bootstrap_allowed(),
        "blocking_message": blocking_message,
        "warnings": [blocking_message] if blocking_message else [],
    }


def image_bank_status(root=None) -> dict:
    """Return operational image-bank status for diagnostics and quality gates."""

    root = Path(root) if root is not None else APP_ROOT
    return image_bank_status_for_paths(get_image_bank_paths(root))


def infer_country_for_city(city, root=None):
    city_key = clean_space(city).lower()
    for candidate in scan_image_bank(get_image_bank_scan_paths(root)):
        if clean_space(candidate.city).lower() == city_key and candidate.country:
            return candidate.country
    return "Custom"
