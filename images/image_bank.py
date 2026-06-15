"""Image-bank path and filename helpers."""

from pathlib import Path, PurePosixPath
import html
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
import zipfile

import diagnostics

from images.remote_distribution import (
    DestinationRequest,
    active_distribution_bank,
    destination_requests_from_rows,
    ensure_destination_packs,
    image_bank_manifest_url,
    schedule_destination_prefetch,
)
from images.scanner import coerce_image_bank_paths, get_image_bank_index, invalidate_image_bank_cache, scan_image_bank

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

    # Destination-specific release packs are the preferred runtime source.
    # They are versioned and activated atomically by remote_distribution.py.
    active_distribution = active_distribution_bank(root)
    if active_distribution is not None:
        paths.append(active_distribution)

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
        "manifest_url": image_bank_manifest_url(),
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


def _extract_full_bank_archive(zip_path: Path, staging_repo: Path) -> int:
    """Safely extract only image_bank_full files into a staged runtime repo."""

    image_count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = PurePosixPath(info.filename.replace("\\", "/"))
            if member.is_absolute() or ".." in member.parts:
                raise RuntimeError(f"Unsafe path in full image-bank archive: {info.filename!r}")
            try:
                bank_index = member.parts.index("image_bank_full")
            except ValueError:
                continue
            relative_parts = member.parts[bank_index:]
            if Path(relative_parts[-1]).suffix.lower() not in {".webp", ".jpg", ".jpeg", ".png", ".avif"}:
                continue
            target = staging_repo.joinpath(*relative_parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            image_count += 1
    return image_count


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

        staging_repo = Path(tempfile.mkdtemp(prefix=".image-bank-full-", dir=runtime_repo.parent))
        try:
            image_count = _extract_full_bank_archive(zip_path, staging_repo)
            staged_bank = staging_repo / "image_bank_full"
            if image_count <= 0 or not _valid_image_bank(staged_bank):
                return _setup_status(
                    False,
                    "zip_missing_image_bank_full",
                    "Downloaded ZIP did not contain image_bank_full with supported images.",
                    method="zip",
                )

            backup = runtime_repo.with_name(f".{runtime_repo.name}.backup-{uuid.uuid4().hex}")
            if runtime_repo.exists():
                os.replace(runtime_repo, backup)
            try:
                os.replace(staging_repo, runtime_repo)
            except Exception:
                if backup.exists() and not runtime_repo.exists():
                    os.replace(backup, runtime_repo)
                raise
            finally:
                if backup.exists():
                    shutil.rmtree(backup, ignore_errors=True)
        except (OSError, zipfile.BadZipFile, RuntimeError) as error:
            return _setup_status(
                False,
                "zip_extract_failed",
                "Could not safely extract and install the image bank ZIP from GitHub.",
                error=f"{type(error).__name__}: {error}",
                method="zip",
            )
        finally:
            if staging_repo.exists():
                shutil.rmtree(staging_repo, ignore_errors=True)

    if _valid_image_bank(runtime_bank):
        return _setup_status(True, "fetched_zip", "Image bank connected from GitHub using ZIP download.", path=runtime_bank, method="zip")

    return _setup_status(False, "zip_install_missing_after_copy", "ZIP image bank install finished, but image_bank_full is missing.", method="zip")


def ensure_runtime_image_bank_status(
    root: Path | str | None = None,
    required_destinations=None,
) -> dict:
    """Explicitly fetch/update the runtime image bank and return diagnostics.

    The image bank remains a separate repository.  This connector installs a
    runtime/cache copy of Dkaalen/itinerary-image-bank/image_bank_full when the
    deployed app cannot see a mounted local copy. For a known itinerary it
    prefers destination release packs, then keeps git and the full repository
    ZIP as compatibility fallbacks.
    """

    root = Path(root) if root is not None else APP_ROOT
    destination_requests = destination_requests_from_rows(required_destinations)
    runtime_repo, runtime_bank = _runtime_bank_paths(root)

    if not destination_requests and _valid_image_bank(runtime_bank):
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

    # Preferred path: fetch only the destinations used by this itinerary from
    # the release manifest.  The legacy full-repository path remains as a safe
    # fallback for older deployments and manifest outages.
    distribution_status = None
    if destination_requests:
        try:
            distribution_status = ensure_destination_packs(root, destination_requests)
            should_refresh_manifest = bool(
                distribution_status.get("manifest_stale")
                or distribution_status.get("unresolved_destinations")
                or any(
                    "checksum mismatch" in str(error).casefold()
                    for error in (distribution_status.get("errors") or [])
                )
            )
            if not distribution_status.get("ok") and should_refresh_manifest:
                refreshed_status = ensure_destination_packs(
                    root,
                    destination_requests,
                    force_manifest_refresh=True,
                )
                refreshed_status["initial_attempt"] = distribution_status
                distribution_status = refreshed_status
        except Exception as error:
            distribution_status = {
                "ok": False,
                "code": "destination_pack_exception",
                "message": "Destination image packs could not be prepared; full-bank fallback will be attempted.",
                "method": "destination_packs",
                "error": f"{type(error).__name__}: {error}",
                "manifest_url": image_bank_manifest_url(),
            }
        if distribution_status.get("ok"):
            invalidate_image_bank_cache()
            return distribution_status

    git_status = _fetch_image_bank_with_git(runtime_repo, runtime_bank)
    if git_status.get("ok"):
        invalidate_image_bank_cache()
        if distribution_status:
            git_status["fallback_from"] = distribution_status.get("code")
            git_status["distribution_error"] = distribution_status.get("error", "")
        return git_status

    zip_status = _fetch_image_bank_with_zip(runtime_repo, runtime_bank)
    if zip_status.get("ok"):
        invalidate_image_bank_cache()
        zip_status["fallback_from"] = git_status.get("code")
        if distribution_status:
            zip_status["distribution_fallback_from"] = distribution_status.get("code")
            zip_status["distribution_error"] = distribution_status.get("error", "")
        return zip_status

    zip_status["fallback_from"] = git_status.get("code")
    zip_status["git_error"] = git_status.get("error", "")
    if distribution_status:
        zip_status["distribution_fallback_from"] = distribution_status.get("code")
        zip_status["distribution_error"] = distribution_status.get("error", "")
    return zip_status


def connect_remote_image_bank_if_missing(
    root: Path | str | None = None,
    required_destinations=None,
) -> dict:
    """Connect the separate remote image-bank repo when no full bank is visible.

    This is app-facing: it may perform network work, but only when called by an
    explicit workflow such as Picture Review or PDF export.  Path lookup remains
    side-effect free.
    """

    root = Path(root) if root is not None else APP_ROOT
    requests = destination_requests_from_rows(required_destinations)
    current = image_bank_status(root, required_destinations=requests)
    if current.get("required_destinations_ready", current.get("full_bank_found")):
        current["setup_status"] = _setup_status(True, "already_connected", "Full destination image bank is already connected.", path=Path(current.get("source_path") or ""), method="existing")
        return current

    setup = ensure_runtime_image_bank_status(root, required_destinations=requests)
    updated = image_bank_status(root, required_destinations=requests)
    updated["setup_status"] = setup
    return updated


def ensure_runtime_image_bank(root: Path | str | None = None, required_destinations=None) -> Path | None:
    """Compatibility wrapper returning only the fetched path when setup succeeds."""

    status = ensure_runtime_image_bank_status(root, required_destinations=required_destinations)
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
    index = get_image_bank_index(scan_paths)
    candidates = index.candidates
    destination_candidates = index.destination_candidates
    default_candidates = index.defaults
    destination_paths = list(index.destination_roots)

    countries = list(index.countries)
    destinations = list(index.destinations)
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
        "manifest_url": image_bank_manifest_url(),
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


def _destination_coverage(index, requests: list[DestinationRequest]) -> tuple[list[str], list[str]]:
    covered: list[str] = []
    missing: list[str] = []
    for request in requests:
        candidates = list(index.candidates_for_city(request.destination, include_defaults=False))
        if request.country:
            country_key = clean_space(request.country).casefold()
            candidates = [candidate for candidate in candidates if clean_space(candidate.country).casefold() == country_key]
        (covered if candidates else missing).append(request.key)
    return covered, missing


def image_bank_status(root=None, required_destinations=None) -> dict:
    """Return operational image-bank status for diagnostics and quality gates."""

    root = Path(root) if root is not None else APP_ROOT
    status = image_bank_status_for_paths(get_image_bank_paths(root))
    requests = destination_requests_from_rows(required_destinations)
    if not requests:
        status["required_destinations_ready"] = bool(status.get("full_bank_found"))
        status["required_destinations"] = []
        status["covered_destinations"] = []
        status["missing_destinations"] = []
        return status

    index = get_image_bank_index(get_image_bank_paths(root))
    covered, missing = _destination_coverage(index, requests)
    status["required_destinations"] = [request.key for request in requests]
    status["covered_destinations"] = covered
    status["missing_destinations"] = missing
    status["required_destinations_ready"] = not missing
    if missing:
        status["blocking_message"] = (
            "Destination pictures are not ready for: " + ", ".join(missing) + ". "
            "The app will download only these destination packs from the separate image bank."
        )
        status["warnings"] = [status["blocking_message"]]
    return status


def prefetch_image_bank_for_rows(rows_or_grouped_days, root=None) -> bool:
    """Start destination-pack prefetch after parsing without blocking the UI."""

    root = Path(root) if root is not None else APP_ROOT
    if not _runtime_bootstrap_allowed():
        return False
    return schedule_destination_prefetch(root, rows_or_grouped_days)


def infer_country_for_city(city, root=None):
    city_key = clean_space(city).lower()
    index = get_image_bank_index(get_image_bank_scan_paths(root))
    for candidate in index.candidates_for_city(city, include_defaults=False):
        if clean_space(candidate.city).lower() == city_key and candidate.country:
            return candidate.country
    return "Custom"
