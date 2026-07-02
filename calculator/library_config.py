"""Configuration for the shared Google Sheets Local Library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

DEFAULT_SPREADSHEET_ID = "1zH-9oPP_pBsq1Pxp0b5eNkniUlBj4DJYVcX13QnYAOA"
DEFAULT_WORKSHEET_NAME = "Local Library"
LOCAL_LIBRARY_SECRET_SECTION = "local_library"
GCP_SERVICE_ACCOUNT_SECRET_SECTION = "gcp_service_account"
_REQUIRED_SERVICE_ACCOUNT_KEYS = frozenset(
    {
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
        "auth_uri",
        "token_uri",
        "auth_provider_x509_cert_url",
        "client_x509_cert_url",
    }
)


@dataclass(frozen=True)
class LocalLibraryConfig:
    """Resolved Local Library connection settings."""

    spreadsheet_id: str = DEFAULT_SPREADSHEET_ID
    worksheet_name: str = DEFAULT_WORKSHEET_NAME
    service_account_info: Mapping[str, str] | None = None
    missing_reason: str = ""

    @property
    def has_google_credentials(self) -> bool:
        """Return whether this config can attempt Google Sheets access."""

        return not self.missing_reason and self.service_account_info is not None


def load_local_library_config(secrets: Mapping[str, object] | None = None) -> LocalLibraryConfig:
    """Load Local Library config from provided or Streamlit secrets."""

    secret_values = secrets if secrets is not None else _streamlit_secrets()
    return local_library_config_from_mapping(secret_values)


def local_library_config_from_mapping(secrets: Mapping[str, object] | None) -> LocalLibraryConfig:
    """Resolve config from a Streamlit-compatible secrets mapping."""

    if not secrets:
        return LocalLibraryConfig(missing_reason="Local Library secrets are missing.")

    library_section = _section(secrets, LOCAL_LIBRARY_SECRET_SECTION)
    service_account = _section(secrets, GCP_SERVICE_ACCOUNT_SECRET_SECTION)
    spreadsheet_id = _text(library_section.get("spreadsheet_id")) or DEFAULT_SPREADSHEET_ID
    worksheet_name = _text(library_section.get("worksheet_name")) or DEFAULT_WORKSHEET_NAME
    service_account_info = _string_mapping(service_account)
    missing_keys = sorted(key for key in _REQUIRED_SERVICE_ACCOUNT_KEYS if not service_account_info.get(key))
    if missing_keys:
        return LocalLibraryConfig(
            spreadsheet_id=spreadsheet_id,
            worksheet_name=worksheet_name,
            missing_reason="Google service account secrets are missing: " + ", ".join(missing_keys),
        )
    return LocalLibraryConfig(
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet_name,
        service_account_info=service_account_info,
    )


def _streamlit_secrets() -> Mapping[str, object] | None:
    try:
        import streamlit as st  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return None
    try:
        return st.secrets  # type: ignore[return-value]
    except Exception:
        return None


def _section(secrets: Mapping[str, object], name: str) -> Mapping[str, object]:
    value = secrets.get(name)
    if isinstance(value, Mapping):
        return value
    return {}


def _string_mapping(values: Mapping[str, object]) -> dict[str, str]:
    return {str(key): _text(value) for key, value in values.items()}


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
