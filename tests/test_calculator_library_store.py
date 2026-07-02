from __future__ import annotations

from typing import Mapping

from calculator.library_config import (
    DEFAULT_SPREADSHEET_ID,
    DEFAULT_WORKSHEET_NAME,
    LocalLibraryConfig,
    local_library_config_from_mapping,
)
from calculator.library_google_sheets import GoogleSheetsLocalLibraryBackend, record_to_sheet_values
from calculator.library_model import LOCAL_LIBRARY_HEADERS, LocalLibraryRow
from calculator.library_store import LocalLibraryStore, local_library_row_to_sheet_mapping


_SERVICE_ACCOUNT = {
    "type": "service_account",
    "project_id": "project",
    "private_key_id": "key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nkey\n-----END PRIVATE KEY-----\n",
    "client_email": "service@example.iam.gserviceaccount.com",
    "client_id": "client-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/service",
}


def test_config_uses_defaults_and_marks_missing_service_account_as_read_only() -> None:
    config = local_library_config_from_mapping({})

    assert config.spreadsheet_id == DEFAULT_SPREADSHEET_ID
    assert config.worksheet_name == DEFAULT_WORKSHEET_NAME
    assert config.has_google_credentials is False
    assert "missing" in config.missing_reason.lower()


def test_config_reads_streamlit_style_sections() -> None:
    config = local_library_config_from_mapping(
        {
            "local_library": {"spreadsheet_id": "sheet-id", "worksheet_name": "Rows"},
            "gcp_service_account": _SERVICE_ACCOUNT,
        }
    )

    assert config.spreadsheet_id == "sheet-id"
    assert config.worksheet_name == "Rows"
    assert config.service_account_info is not None
    assert config.service_account_info["client_email"] == "service@example.iam.gserviceaccount.com"
    assert config.has_google_credentials is True


def test_store_uses_fixture_fallback_when_credentials_are_missing() -> None:
    store = LocalLibraryStore(config=LocalLibraryConfig(missing_reason="No secrets configured."))

    result = store.list_rows()

    assert result.source == "fixture"
    assert result.read_only is True
    assert result.rows
    assert all(row.is_available_for_fetch for row in store.list_fetchable_rows())


def test_store_normalizes_google_backend_records() -> None:
    backend = _FakeBackend(
        records=(
            {
                "library_id": "lib_1",
                "is_deleted": "FALSE",
                "is_fetchable": "TRUE",
                "record_type": "line",
                "Type": "Activity",
                "Travel element": "Northern lights chase",
                "Gross P per unit": "1200",
                "Units": "2",
                "Supp curr": "nok",
                "Sales curr": "nok",
            },
            {
                "library_id": "lib_2",
                "is_deleted": "TRUE",
                "is_fetchable": "TRUE",
                "record_type": "line",
                "Travel element": "Deleted row",
            },
        )
    )
    store = LocalLibraryStore(config=_google_config(), backend=backend)

    result = store.list_rows()

    assert result.source == "google_sheets"
    assert result.read_only is False
    assert len(result.rows) == 2
    assert result.rows[0].travel_element == "Northern lights chase"
    assert result.rows[0].gross_price_per_unit == 1200
    assert result.rows[0].supplier_currency == "NOK"
    assert [row.library_id for row in store.list_fetchable_rows()] == ["lib_1"]


def test_store_saves_rows_to_backend_with_sheet_headers() -> None:
    backend = _FakeBackend(records=())
    store = LocalLibraryStore(config=_google_config(), backend=backend)

    result = store.save_row(LocalLibraryRow(library_id="lib_3", travel_element="Oslo hotel", is_fetchable=True))

    assert result.ok is True
    assert result.read_only is False
    assert backend.saved_records[0]["library_id"] == "lib_3"
    assert backend.saved_records[0]["Travel element"] == "Oslo hotel"
    assert backend.saved_records[0]["is_fetchable"] is True


def test_row_to_sheet_mapping_uses_google_sheet_headers() -> None:
    row = LocalLibraryRow(library_id="lib_4", travel_element="Fjord cruise")

    mapping = local_library_row_to_sheet_mapping(row)

    assert tuple(mapping) == LOCAL_LIBRARY_HEADERS
    assert mapping["library_id"] == "lib_4"
    assert mapping["Travel element"] == "Fjord cruise"


def test_google_backend_updates_existing_library_id() -> None:
    worksheet = _FakeWorksheet(
        records=[{"library_id": "lib_5", "Travel element": "Old"}],
        headers=("library_id", "Travel element", "is_fetchable"),
    )
    backend = GoogleSheetsLocalLibraryBackend(_google_config(), client_factory=_client_factory(worksheet))

    result = backend.upsert_record({"library_id": "lib_5", "Travel element": "New", "is_fetchable": True})

    assert result.action == "updated"
    assert worksheet.updated_range == "A2:C2"
    assert worksheet.updated_values == [["lib_5", "New", "TRUE"]]


def test_google_backend_appends_new_library_id() -> None:
    worksheet = _FakeWorksheet(records=[], headers=("library_id", "Travel element"))
    backend = GoogleSheetsLocalLibraryBackend(_google_config(), client_factory=_client_factory(worksheet))

    result = backend.upsert_record({"library_id": "lib_6", "Travel element": "New line"})

    assert result.action == "appended"
    assert worksheet.appended_values == [["lib_6", "New line"]]


def test_record_to_sheet_values_converts_booleans_and_missing_values() -> None:
    assert record_to_sheet_values({"a": True, "b": False}, ("a", "b", "c")) == ["TRUE", "FALSE", ""]


def _google_config() -> LocalLibraryConfig:
    return LocalLibraryConfig(
        spreadsheet_id="sheet-id",
        worksheet_name="Local Library",
        service_account_info=_SERVICE_ACCOUNT,
    )


class _FakeBackend:
    def __init__(self, records: tuple[Mapping[str, object], ...]) -> None:
        self._records = records
        self.saved_records: list[Mapping[str, object]] = []

    def list_records(self) -> tuple[Mapping[str, object], ...]:
        return self._records

    def upsert_record(self, record: Mapping[str, object]) -> None:
        self.saved_records.append(record)


class _FakeWorksheet:
    def __init__(self, records: list[Mapping[str, object]], headers: tuple[str, ...]) -> None:
        self._records = records
        self._headers = headers
        self.updated_range = ""
        self.updated_values: list[list[object]] = []
        self.appended_values: list[list[object]] = []

    def get_all_records(self, default_blank: str = "") -> list[Mapping[str, object]]:
        return self._records

    def row_values(self, row_number: int) -> tuple[str, ...]:
        assert row_number == 1
        return self._headers

    def update(self, range_name: str, values: list[list[object]], value_input_option: str) -> None:
        assert value_input_option == "USER_ENTERED"
        self.updated_range = range_name
        self.updated_values = values

    def append_row(self, values: list[object], value_input_option: str) -> None:
        assert value_input_option == "USER_ENTERED"
        self.appended_values.append(values)


class _FakeSpreadsheet:
    def __init__(self, worksheet: _FakeWorksheet) -> None:
        self._worksheet = worksheet

    def worksheet(self, worksheet_name: str) -> _FakeWorksheet:
        assert worksheet_name == "Local Library"
        return self._worksheet


class _FakeClient:
    def __init__(self, worksheet: _FakeWorksheet) -> None:
        self._worksheet = worksheet

    def open_by_key(self, spreadsheet_id: str) -> _FakeSpreadsheet:
        assert spreadsheet_id == "sheet-id"
        return _FakeSpreadsheet(self._worksheet)


def _client_factory(worksheet: _FakeWorksheet):
    def factory(service_account_info: Mapping[str, str]) -> _FakeClient:
        assert service_account_info["client_email"] == "service@example.iam.gserviceaccount.com"
        return _FakeClient(worksheet)

    return factory
