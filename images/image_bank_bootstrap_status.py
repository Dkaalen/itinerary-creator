"""Stable status payload helpers for image-bank bootstrap attempts."""

from dataclasses import asdict, dataclass
from pathlib import Path

import diagnostics

from images.image_bank_discovery import valid_image_bank
from images.image_bank_settings import bootstrap_status_metadata, clean_space, runtime_bootstrap_allowed


@dataclass(frozen=True, slots=True)
class ImageBankBootstrapResult:
    """Stable public status contract for runtime image-bank setup."""

    ok: bool
    code: str
    message: str
    path: str = ""
    method: str = ""
    source: str = ""
    error: str = ""
    fallback_used: bool = False
    degraded: bool = False
    cache_available: bool = False
    git_attempted: bool = False
    git_error: str = ""
    zip_attempted: bool = False
    zip_error: str = ""
    distribution_attempted: bool = False
    distribution_error: str = ""

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload.update({"diagnostic_code": self.code, **bootstrap_status_metadata()})
        return payload


def setup_status(
    ok: bool,
    code: str,
    message: str,
    *,
    path: Path | None = None,
    error: str = "",
    method: str = "",
    source: str = "",
    fallback_used: bool = False,
    degraded: bool = False,
    cache_available: bool = False,
    warn: bool = True,
) -> dict:
    method = clean_space(method)
    error = clean_space(error)
    payload = ImageBankBootstrapResult(
        ok=bool(ok),
        code=code,
        message=message,
        path=str(path or ""),
        method=method,
        source=clean_space(source) or method,
        error=error,
        fallback_used=bool(fallback_used),
        degraded=bool(degraded),
        cache_available=bool(cache_available or (path and valid_image_bank(path))),
        git_attempted=method == "git",
        git_error=error if method == "git" else "",
        zip_attempted=method == "zip",
        zip_error=error if method == "zip" else "",
        distribution_attempted=method == "destination_packs",
        distribution_error=error if method == "destination_packs" else "",
    ).to_dict()
    if not ok:
        if warn:
            diagnostics.warn("image_bank_setup", message, error, source="images.image_bank")
    return payload


def stage_error(status: dict | None) -> str:
    if not status:
        return ""
    error = clean_space(status.get("error", ""))
    if error:
        return error
    errors = status.get("errors")
    if isinstance(errors, (list, tuple)):
        return "; ".join(clean_space(value) for value in errors if clean_space(value))
    return clean_space(status.get("message", "")) if not status.get("ok") else ""


def merge_attempts(
    status: dict,
    *,
    distribution_status: dict | None = None,
    git_status: dict | None = None,
    zip_status: dict | None = None,
) -> dict:
    """Attach deterministic attempt diagnostics to a final setup result."""

    payload = dict(status)
    payload["distribution_attempted"] = distribution_status is not None
    payload["distribution_error"] = stage_error(distribution_status)
    payload["git_attempted"] = git_status is not None
    payload["git_error"] = stage_error(git_status)
    payload["zip_attempted"] = zip_status is not None
    payload["zip_error"] = stage_error(zip_status)
    attempted = sum(bool(item) for item in (distribution_status, git_status, zip_status))
    payload["fallback_used"] = bool(payload.get("fallback_used") or attempted > 1)
    if git_status is not None and zip_status is not None:
        payload["fallback_from"] = git_status.get("code", "")
    elif distribution_status is not None and (git_status is not None or zip_status is not None):
        payload["fallback_from"] = distribution_status.get("code", "")
    if distribution_status is not None and git_status is not None and zip_status is not None:
        payload["distribution_fallback_from"] = distribution_status.get("code", "")
    return payload


def normalise_stage_status(status: dict | None, method: str) -> dict:
    """Apply the stable bootstrap fields to connector-specific status payloads."""

    raw = dict(status or {})
    path_text = clean_space(raw.get("path", ""))
    base = setup_status(
        bool(raw.get("ok")),
        clean_space(raw.get("code", "")) or f"{method}_unknown",
        clean_space(raw.get("message", "")) or "Image-bank setup returned no status message.",
        path=Path(path_text) if path_text else None,
        error=stage_error(raw),
        method=clean_space(raw.get("method", "")) or method,
        source=clean_space(raw.get("source", "")) or method,
        cache_available=bool(raw.get("cache_available")),
        degraded=bool(raw.get("degraded")),
        fallback_used=bool(raw.get("fallback_used")),
        warn=False,
    )
    base.update(raw)
    base["diagnostic_code"] = clean_space(base.get("code", ""))
    base["bootstrap_allowed"] = runtime_bootstrap_allowed()
    return base
