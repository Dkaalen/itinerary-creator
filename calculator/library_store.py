"""Read-only storage facade for the authoritative bundled workbook."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from calculator.library_authority import (
    LOCAL_LIBRARY_AUTHORITY_ID,
    LocalLibraryDiagnostic,
    LocalLibraryWorkbookError,
    load_local_library_authority,
)
from calculator.library_model import LocalLibraryRow


@dataclass(frozen=True)
class LocalLibraryReadResult:
    rows: tuple[LocalLibraryRow, ...]
    source: str
    read_only: bool
    message: str = ""
    currency_rates: Mapping[str, float] | None = None
    fingerprint: str = ""
    diagnostics: tuple[LocalLibraryDiagnostic, ...] = ()
    error_category: str = ""
    load_time_seconds: float = 0.0
    authority_id: str = LOCAL_LIBRARY_AUTHORITY_ID
    supported_worksheets: tuple[str, ...] = ()
    cache_status: str = ""
    cache_invalidation_reason: str = ""


class LocalLibraryStore:
    """Expose the bundled workbook as the sole production Local Library source."""

    def list_rows(self) -> LocalLibraryReadResult:
        try:
            authority = load_local_library_authority()
        except LocalLibraryWorkbookError as exc:
            return LocalLibraryReadResult(
                rows=(),
                source="local_excel",
                read_only=True,
                message=str(exc),
                currency_rates=MappingProxyType({}),
                diagnostics=exc.diagnostics,
                error_category=exc.category,
            )
        return LocalLibraryReadResult(
            rows=authority.records,
            source="local_excel",
            read_only=True,
            currency_rates=authority.currency_rates,
            fingerprint=authority.fingerprint,
            diagnostics=authority.diagnostics,
            authority_id=authority.authority_id,
            supported_worksheets=authority.supported_worksheets,
            cache_status=authority.cache_status,
            cache_invalidation_reason=authority.cache_invalidation_reason,
        )

    def list_fetchable_rows(self) -> tuple[LocalLibraryRow, ...]:
        return tuple(row for row in self.list_rows().rows if row.is_available_for_fetch)
