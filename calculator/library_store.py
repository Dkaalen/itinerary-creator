"""Read-only storage facade for the bundled Excel Local Library."""
from __future__ import annotations
from dataclasses import dataclass
from calculator.library_model import LocalLibraryRow
from calculator.library_workbook import LocalLibraryWorkbookError, load_local_library_workbook

@dataclass(frozen=True)
class LocalLibraryReadResult:
    rows: tuple[LocalLibraryRow, ...]
    source: str
    read_only: bool
    message: str = ""
    currency_rates: dict[str, float] | None = None

@dataclass(frozen=True)
class LocalLibraryWriteResult:
    ok: bool
    source: str
    read_only: bool
    message: str

class LocalLibraryStore:
    """Expose the repository-local workbook as the sole Local Library source."""
    def list_rows(self) -> LocalLibraryReadResult:
        try:
            library = load_local_library_workbook()
        except LocalLibraryWorkbookError as exc:
            return LocalLibraryReadResult((), "local_excel", True, str(exc), {})
        return LocalLibraryReadResult(library.rows, "local_excel", True, "", dict(library.currency_rates))

    def list_fetchable_rows(self) -> tuple[LocalLibraryRow, ...]:
        return tuple(row for row in self.list_rows().rows if row.is_available_for_fetch)

    def save_row(self, row: LocalLibraryRow) -> LocalLibraryWriteResult:
        return LocalLibraryWriteResult(False, "local_excel", True, "Edit the bundled Excel workbook and redeploy to change the Local Library.")
