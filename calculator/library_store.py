"""Storage facade for Local Library rows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Protocol

from calculator.library_config import LocalLibraryConfig, load_local_library_config
from calculator.library_fixture import fallback_library_rows
from calculator.library_google_sheets import GoogleSheetsLibraryError, GoogleSheetsLocalLibraryBackend
from calculator.library_model import LOCAL_LIBRARY_COLUMNS, LocalLibraryRow
from calculator.library_normalize import normalize_library_rows


class LocalLibraryBackend(Protocol):
    """Backend interface used by the Local Library store."""

    def list_records(self) -> tuple[Mapping[str, object], ...]:
        """Return raw Local Library records."""

    def upsert_record(self, record: Mapping[str, object]) -> object:
        """Append or update one raw Local Library record."""


@dataclass(frozen=True)
class LocalLibraryReadResult:
    """Rows plus metadata from a Local Library read."""

    rows: tuple[LocalLibraryRow, ...]
    source: str
    read_only: bool
    message: str = ""


@dataclass(frozen=True)
class LocalLibraryWriteResult:
    """Result from a Local Library write."""

    ok: bool
    source: str
    read_only: bool
    message: str


class LocalLibraryStore:
    """Read/write Local Library rows with fixture fallback."""

    def __init__(
        self,
        config: LocalLibraryConfig | None = None,
        *,
        backend: LocalLibraryBackend | None = None,
    ) -> None:
        self._config = config or load_local_library_config()
        self._backend = backend

    def list_rows(self) -> LocalLibraryReadResult:
        """Return normalized rows from Google Sheets or the read-only fixture."""

        if not self._config.has_google_credentials and self._backend is None:
            return self._fallback_result(self._config.missing_reason)
        try:
            records = self._active_backend().list_records()
            return LocalLibraryReadResult(rows=normalize_library_rows(records), source="google_sheets", read_only=False)
        except GoogleSheetsLibraryError as exc:
            return self._fallback_result(str(exc))

    def list_fetchable_rows(self) -> tuple[LocalLibraryRow, ...]:
        """Return rows that are active and fetchable."""

        return tuple(row for row in self.list_rows().rows if row.is_available_for_fetch)

    def save_row(self, row: LocalLibraryRow) -> LocalLibraryWriteResult:
        """Write one row to Google Sheets when credentials are available."""

        if not self._config.has_google_credentials and self._backend is None:
            return LocalLibraryWriteResult(
                ok=False,
                source="fixture",
                read_only=True,
                message=self._config.missing_reason or "Local Library is read-only because Google Sheets is not configured.",
            )
        try:
            self._active_backend().upsert_record(local_library_row_to_sheet_mapping(row))
            return LocalLibraryWriteResult(ok=True, source="google_sheets", read_only=False, message="Saved Local Library row.")
        except GoogleSheetsLibraryError as exc:
            return LocalLibraryWriteResult(ok=False, source="google_sheets", read_only=False, message=str(exc))

    def _active_backend(self) -> LocalLibraryBackend:
        return self._backend or GoogleSheetsLocalLibraryBackend(self._config)

    def _fallback_result(self, reason: str = "") -> LocalLibraryReadResult:
        message = reason or "Using bundled read-only Local Library fixture."
        return LocalLibraryReadResult(rows=fallback_library_rows(), source="fixture", read_only=True, message=message)


def local_library_row_to_sheet_mapping(row: LocalLibraryRow) -> dict[str, object]:
    """Return a sheet-header-keyed mapping for one Local Library row."""

    values_by_field = asdict(row)
    return {column.header: values_by_field[column.field_name] for column in LOCAL_LIBRARY_COLUMNS}
