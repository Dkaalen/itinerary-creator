"""Runtime fetch/install helpers for the separate itinerary image bank."""

from pathlib import Path, PurePosixPath
import os as default_os
import shutil as default_shutil
import socket
import subprocess as default_subprocess
import tempfile
import urllib.error as default_urllib_error
import urllib.request as default_urllib_request
import uuid
import zipfile

from images.image_bank_bootstrap_status import setup_status
from images.image_bank_discovery import valid_image_bank
from images.image_bank_settings import SUPPORTED_IMAGE_EXTENSIONS, image_bank_repo_branch, image_bank_repo_url, repo_zip_url
from images.remote_distribution_config import network_timeout_seconds


def fetch_image_bank_with_git(
    runtime_repo: Path,
    runtime_bank: Path,
    *,
    shutil_module=default_shutil,
    subprocess_module=default_subprocess,
) -> dict:
    if shutil_module.which("git") is None:
        return setup_status(
            False,
            "git_missing",
            "git is not available; ZIP download fallback will be attempted.",
            method="git",
            warn=False,
        )

    command = ["git", "clone", "--depth", "1", "--branch", image_bank_repo_branch(), image_bank_repo_url(), str(runtime_repo)]
    if runtime_repo.exists() and (runtime_repo / ".git").exists():
        command = ["git", "-C", str(runtime_repo), "pull", "--ff-only"]

    try:
        result = subprocess_module.run(
            command,
            check=False,
            stdout=subprocess_module.PIPE,
            stderr=subprocess_module.PIPE,
            timeout=180 if "clone" in command else 60,
            text=True,
        )
    except (OSError, default_subprocess.SubprocessError) as error:
        return setup_status(
            False,
            "git_command_failed",
            "Git could not fetch the image bank; ZIP download fallback will be attempted.",
            error=f"{type(error).__name__}: {error}",
            method="git",
            warn=False,
        )

    if result.returncode != 0:
        error_text = " ".join((result.stderr or result.stdout or "").split())[:600]
        return setup_status(
            False,
            "git_returned_error",
            "Git could not fetch the image bank; ZIP download fallback will be attempted.",
            error=error_text,
            method="git",
            warn=False,
        )

    if valid_image_bank(runtime_bank):
        return setup_status(
            True,
            "fetched_git",
            "Image bank connected from GitHub using git.",
            path=runtime_bank,
            method="git",
            source="git",
        )

    return setup_status(
        False,
        "image_bank_missing_after_git_fetch",
        "Git finished, but image_bank_full was not found; ZIP download fallback will be attempted.",
        method="git",
        warn=False,
    )


def extract_full_bank_archive(zip_path: Path, staging_repo: Path) -> int:
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
            if Path(relative_parts[-1]).suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                continue
            target = staging_repo.joinpath(*relative_parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("wb") as output:
                default_shutil.copyfileobj(source, output, length=1024 * 1024)
            image_count += 1
    return image_count


def fetch_image_bank_with_zip(
    runtime_repo: Path,
    runtime_bank: Path,
    *,
    os_module=default_os,
    shutil_module=default_shutil,
    urllib_request_module=default_urllib_request,
    urllib_error_module=default_urllib_error,
    extract_archive=extract_full_bank_archive,
) -> dict:
    zip_url = repo_zip_url()
    try:
        runtime_repo.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return setup_status(
            False,
            "runtime_dir_failed",
            "Could not create the runtime image-bank folder.",
            error=f"{type(error).__name__}: {error}",
            method="zip",
            warn=False,
        )

    try:
        temporary_context = tempfile.TemporaryDirectory(prefix="image-bank-zip-")
    except OSError as error:
        return setup_status(
            False,
            "zip_staging_failed",
            "Could not create temporary storage for the image-bank ZIP.",
            error=f"{type(error).__name__}: {error}",
            method="zip",
            warn=False,
        )

    with temporary_context as tmp_text:
        tmp = Path(tmp_text)
        zip_path = tmp / "image-bank.zip"
        try:
            previous_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(network_timeout_seconds())
            try:
                urllib_request_module.urlretrieve(zip_url, zip_path)
            finally:
                socket.setdefaulttimeout(previous_timeout)
        except (OSError, urllib_error_module.URLError, ValueError, TimeoutError) as error:
            status = setup_status(
                False,
                "zip_download_failed",
                "Could not download the image bank ZIP from GitHub within the network timeout.",
                error=f"{type(error).__name__}: {error}",
                method="zip",
                warn=False,
            )
            status["timeout_seconds"] = network_timeout_seconds()
            return status

        try:
            staging_repo = Path(tempfile.mkdtemp(prefix=".image-bank-full-", dir=runtime_repo.parent))
        except OSError as error:
            return setup_status(
                False,
                "zip_staging_failed",
                "Could not create the staged image-bank installation folder.",
                error=f"{type(error).__name__}: {error}",
                method="zip",
                warn=False,
            )
        try:
            image_count = extract_archive(zip_path, staging_repo)
            staged_bank = staging_repo / "image_bank_full"
            if image_count <= 0 or not valid_image_bank(staged_bank):
                return setup_status(
                    False,
                    "zip_missing_image_bank_full",
                    "Downloaded ZIP did not contain image_bank_full with supported images.",
                    method="zip",
                    warn=False,
                )

            backup = runtime_repo.with_name(f".{runtime_repo.name}.backup-{uuid.uuid4().hex}")
            if runtime_repo.exists():
                os_module.replace(runtime_repo, backup)
            replacement_committed = False
            try:
                os_module.replace(staging_repo, runtime_repo)
                replacement_committed = True
            except OSError as install_error:
                if backup.exists() and not runtime_repo.exists():
                    try:
                        os_module.replace(backup, runtime_repo)
                        replacement_committed = True
                    except OSError as rollback_error:
                        raise RuntimeError(
                            "Image-bank install failed and the previous bank could not be restored; "
                            f"the backup was retained at {backup}. Install error: {install_error}. "
                            f"Rollback error: {rollback_error}."
                        ) from rollback_error
                raise
            finally:
                if replacement_committed and backup.exists():
                    shutil_module.rmtree(backup, ignore_errors=True)
        except (OSError, zipfile.BadZipFile, RuntimeError) as error:
            return setup_status(
                False,
                "zip_extract_failed",
                "Could not safely extract and install the image bank ZIP from GitHub.",
                error=f"{type(error).__name__}: {error}",
                method="zip",
                warn=False,
            )
        finally:
            if staging_repo.exists():
                shutil_module.rmtree(staging_repo, ignore_errors=True)

    if valid_image_bank(runtime_bank):
        return setup_status(
            True,
            "fetched_zip",
            "Image bank connected from GitHub using ZIP download.",
            path=runtime_bank,
            method="zip",
            source="zip",
            fallback_used=True,
        )

    return setup_status(
        False,
        "zip_install_missing_after_copy",
        "ZIP image bank install finished, but image_bank_full is missing.",
        method="zip",
        warn=False,
    )
