"""Read-only storage facade for the bundled Excel Local Library."""

from __future__ import annotations

from dataclasses import dataclass

from calculator.library_model import LocalLibraryRow
from calculator.library_workbook import (
    LocalLibraryDiagnostic,
    LocalLibraryWorkbookError,
    load_local_library_workbook,
)


@dataclass(frozen=True)
class LocalLibraryReadResult:
    rows: tuple[LocalLibraryRow, ...]
    source: str
    read_only: bool
    message: str = ""
    currency_rates: dict[str, float] | None = None
    fingerprint: str = ""
    diagnostics: tuple[LocalLibraryDiagnostic, ...] = ()
    error_category: str = ""
    load_time_seconds: float = 0.0


class LocalLibraryStore:
    """Expose the repository-local workbook as the sole Local Library source."""

    def list_rows(self) -> LocalLibraryReadResult:
        try:
            library = load_local_library_workbook()
        except LocalLibraryWorkbookError as exc:
            return LocalLibraryReadResult(
                (),
                "local_excel",
                True,
                str(exc),
                {},
                "",
                exc.diagnostics,
                exc.category,
            )
        return LocalLibraryReadResult(
            library.rows,
            "local_excel",
            True,
            "",
            dict(library.currency_rates),
            library.fingerprint,
            library.diagnostics,
        )

    def list_fetchable_rows(self) -> tuple[LocalLibraryRow, ...]:
        return tuple(row for row in self.list_rows().rows if row.is_available_for_fetch)
