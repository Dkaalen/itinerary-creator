"""Single production authority for the bundled Local Library workbook.

Production callers use this module rather than selecting a storage backend.
The workbook parser remains an implementation detail; this boundary exposes
path, content fingerprint, supported worksheets, immutable records, stable
source identity, and cache lifecycle metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from typing import Mapping

from calculator.library_fingerprint import local_library_workbook_fingerprint
from calculator.library_identity import LOCAL_LIBRARY_AUTHORITY_ID
from calculator.library_model import LocalLibraryRow
from calculator.library_workbook import (
    WORKBOOK_PATH,
    clear_local_library_workbook_cache,
    load_local_library_workbook,
)
from calculator.library_workbook_models import LocalLibraryDiagnostic, LocalLibraryWorkbookError
from calculator.library_workbook_schema import REQUIRED_SHEETS

_CACHE_LOCK = RLock()
_CACHE: dict[str, "LocalLibraryAuthorityRead"] = {}
_CLEAR_REASON: dict[str, str] = {}


@dataclass(frozen=True)
class LocalLibraryAuthorityRead:
    """One immutable read from the authoritative workbook boundary."""

    authority_id: str
    path: Path
    fingerprint: str
    supported_worksheets: tuple[str, ...]
    records: tuple[LocalLibraryRow, ...]
    currency_rates: Mapping[str, float]
    diagnostics: tuple[LocalLibraryDiagnostic, ...] = ()
    cache_status: str = "miss"
    cache_invalidation_reason: str = "initial_load"

    @property
    def invalid_records(self) -> tuple[LocalLibraryDiagnostic, ...]:
        return tuple(issue for issue in self.diagnostics if issue.category == "invalid_record")

    @property
    def warnings(self) -> tuple[LocalLibraryDiagnostic, ...]:
        return tuple(issue for issue in self.diagnostics if issue.category == "warning")

    def source_identity(self, row: LocalLibraryRow) -> str:
        """Return the canonical source identity for one authoritative record."""

        return row.source_identity


def load_local_library_authority(path: str | Path = WORKBOOK_PATH) -> LocalLibraryAuthorityRead:
    """Read the sole production Local Library authority with content invalidation."""

    workbook_path = Path(path)
    if not workbook_path.is_file():
        raise LocalLibraryWorkbookError(
            f"Local Library workbook is missing: {workbook_path}",
            category="fatal_workbook",
            code="missing_workbook",
        )
    resolved = workbook_path.resolve()
    path_key = str(resolved)
    fingerprint = local_library_workbook_fingerprint(resolved)

    with _CACHE_LOCK:
        cached = _CACHE.get(path_key)
        if cached is not None and cached.fingerprint == fingerprint:
            return replace(cached, cache_status="hit", cache_invalidation_reason="unchanged")
        if cached is not None:
            reason = "workbook_content_changed"
        else:
            reason = _CLEAR_REASON.pop(path_key, "initial_load")

    # Parse outside the authority lock. Failed reads never replace a known-good
    # cached snapshot and therefore cannot poison the next attempt.
    workbook = load_local_library_workbook(resolved)
    read = LocalLibraryAuthorityRead(
        authority_id=LOCAL_LIBRARY_AUTHORITY_ID,
        path=workbook.path,
        fingerprint=workbook.fingerprint,
        supported_worksheets=tuple(REQUIRED_SHEETS),
        records=workbook.rows,
        currency_rates=MappingProxyType(dict(workbook.currency_rates)),
        diagnostics=workbook.diagnostics,
        cache_status="miss",
        cache_invalidation_reason=reason,
    )
    with _CACHE_LOCK:
        _CACHE[path_key] = read
    return read


def clear_local_library_authority_cache(path: str | Path | None = None) -> None:
    """Clear parsed authority state and force browser rehydration on next read."""

    with _CACHE_LOCK:
        if path is None:
            keys = tuple(_CACHE) or (str(WORKBOOK_PATH.resolve()),)
            _CACHE.clear()
            for key in keys:
                _CLEAR_REASON[key] = "explicit_cache_clear"
        else:
            key = str(Path(path).resolve())
            _CACHE.pop(key, None)
            _CLEAR_REASON[key] = "explicit_cache_clear"
    clear_local_library_workbook_cache()


def local_library_authority_path() -> Path:
    return WORKBOOK_PATH


def local_library_supported_worksheets() -> tuple[str, ...]:
    return tuple(REQUIRED_SHEETS)


__all__ = [
    "LOCAL_LIBRARY_AUTHORITY_ID",
    "LocalLibraryAuthorityRead",
    "LocalLibraryDiagnostic",
    "LocalLibraryWorkbookError",
    "clear_local_library_authority_cache",
    "load_local_library_authority",
    "local_library_authority_path",
    "local_library_supported_worksheets",
]
