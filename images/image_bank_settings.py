"""Configuration helpers for the external itinerary image bank."""

from pathlib import Path
import html
import os

from images.remote_distribution import image_bank_manifest_url

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE_BANK_REPO_URL = "https://github.com/Dkaalen/itinerary-image-bank.git"
DEFAULT_IMAGE_BANK_REPO_BRANCH = "main"
RUNTIME_IMAGE_BANK_DIR = ".runtime_image_bank"
SUPPORTED_IMAGE_EXTENSIONS = frozenset({".webp", ".jpg", ".jpeg", ".png", ".avif"})


def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def image_bank_repo_url() -> str:
    return clean_space(os.environ.get("ITINERARY_IMAGE_BANK_REPO_URL", "")) or DEFAULT_IMAGE_BANK_REPO_URL


def image_bank_repo_branch() -> str:
    return clean_space(os.environ.get("ITINERARY_IMAGE_BANK_REPO_BRANCH", "")) or DEFAULT_IMAGE_BANK_REPO_BRANCH


def esc(value):
    return html.escape(str(value or ""), quote=True)


def runtime_bootstrap_allowed() -> bool:
    """Return whether the app may fetch the image-bank repo at runtime.

    The full destination image bank is a separate repository and is required for
    good Add Pictures results. Local/sibling checkouts remain preferred, but a
    missing full bank should not silently degrade to the tiny bundled Default
    folder. Runtime bootstrap is therefore on by default and can be disabled
    explicitly with ``ITINERARY_IMAGE_BANK_BOOTSTRAP=0``.

    This function deliberately does not inspect test-runner environment variables.
    Tests and deployments must control network behaviour through the documented
    application setting, just like production.
    """

    value = clean_space(os.environ.get("ITINERARY_IMAGE_BANK_BOOTSTRAP", "")).lower()
    if value in {"0", "false", "no", "off", "disabled"}:
        return False
    if value in {"1", "true", "yes", "on", "enabled"}:
        return True
    return True


def repo_zip_url() -> str:
    """Return the GitHub archive URL for the configured image-bank repo."""

    repo_url = image_bank_repo_url()
    branch = image_bank_repo_branch()
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    return repo_url.rstrip("/") + f"/archive/refs/heads/{branch}.zip"


def bootstrap_status_metadata() -> dict:
    return {
        "repo_url": image_bank_repo_url(),
        "branch": image_bank_repo_branch(),
        "zip_url": repo_zip_url(),
        "manifest_url": image_bank_manifest_url(),
        "bootstrap_allowed": runtime_bootstrap_allowed(),
    }
