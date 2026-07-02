"""Google Sheets I/O for Local Library records."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from calculator.library_config import LocalLibraryConfig
from calculator.library_model import LOCAL_LIBRARY_HEADERS

ClientFactory = Callable[[Mapping[str, str]], object]


class GoogleSheetsLibraryError(RuntimeError):
    """Raised when Google Sheets access fails."""


@dataclass(frozen=True)
class GoogleSheetsWriteResult:
    """Result from a Google Sheets write operation."""

    action: str
    library_id: str


class GoogleSheetsLocalLibraryBackend:
    """Read and write Local Library sheet records through Google Sheets."""

    def __init__(
        self,
        config: LocalLibraryConfig,
        *,
        client_factory: ClientFactory | None = None,
        headers: Sequence[str] = LOCAL_LIBRARY_HEADERS,
    ) -> None:
        self._config = config
        self._client_factory = client_factory
        self._headers = tuple(headers)

    def list_records(self) -> tuple[Mapping[str, object], ...]:
        """Return raw sheet records keyed by header."""

        worksheet = self._worksheet()
        try:
            return tuple(worksheet.get_all_records(default_blank=""))
        except Exception as exc:  # pragma: no cover - exercised by integration/runtime failures
            raise GoogleSheetsLibraryError(f"Could not read Local Library worksheet: {exc}") from exc

    def upsert_record(self, record: Mapping[str, object]) -> GoogleSheetsWriteResult:
        """Append or update a raw record using library_id as the stable key."""

        library_id = str(record.get("library_id") or "").strip()
        if not library_id:
            raise GoogleSheetsLibraryError("Cannot write Local Library row without library_id.")
        worksheet = self._worksheet()
        try:
            headers = _worksheet_headers(worksheet) or self._headers
            values = record_to_sheet_values(record, headers)
            existing_row_number = _find_row_number_by_library_id(worksheet, library_id)
            if existing_row_number:
                end_column = _column_label(len(headers))
                worksheet.update(
                    f"A{existing_row_number}:{end_column}{existing_row_number}",
                    [values],
                    value_input_option="USER_ENTERED",
                )
                return GoogleSheetsWriteResult(action="updated", library_id=library_id)
            worksheet.append_row(values, value_input_option="USER_ENTERED")
            return GoogleSheetsWriteResult(action="appended", library_id=library_id)
        except GoogleSheetsLibraryError:
            raise
        except Exception as exc:  # pragma: no cover - exercised by integration/runtime failures
            raise GoogleSheetsLibraryError(f"Could not write Local Library row: {exc}") from exc

    def _worksheet(self) -> Any:
        if not self._config.has_google_credentials or self._config.service_account_info is None:
            raise GoogleSheetsLibraryError(self._config.missing_reason or "Google Sheets credentials are missing.")
        try:
            client = self._client_factory(self._config.service_account_info) if self._client_factory else _gspread_client(self._config.service_account_info)
            return client.open_by_key(self._config.spreadsheet_id).worksheet(self._config.worksheet_name)
        except GoogleSheetsLibraryError:
            raise
        except Exception as exc:  # pragma: no cover - exercised by integration/runtime failures
            raise GoogleSheetsLibraryError(f"Could not open Local Library worksheet: {exc}") from exc


def record_to_sheet_values(record: Mapping[str, object], headers: Sequence[str]) -> list[object]:
    """Return row values ordered for the worksheet headers."""

    return [_sheet_value(record.get(header, "")) for header in headers]


def _gspread_client(service_account_info: Mapping[str, str]) -> object:
    try:
        import gspread  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise GoogleSheetsLibraryError("gspread is not installed.") from exc
    return gspread.service_account_from_dict(dict(service_account_info))


def _worksheet_headers(worksheet: object) -> tuple[str, ...]:
    headers = tuple(str(value).strip() for value in worksheet.row_values(1))
    return tuple(header for header in headers if header)


def _find_row_number_by_library_id(worksheet: object, library_id: str) -> int | None:
    records = worksheet.get_all_records(default_blank="")
    for index, record in enumerate(records, start=2):
        if str(record.get("library_id") or "").strip() == library_id:
            return index
    return None


def _column_label(column_number: int) -> str:
    label = ""
    number = column_number
    while number:
        number, remainder = divmod(number - 1, 26)
        label = chr(65 + remainder) + label
    return label or "A"


def _sheet_value(value: object) -> object:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None:
        return ""
    return value
