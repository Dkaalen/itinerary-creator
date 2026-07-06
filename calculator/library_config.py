"""Configuration for the shared Google Sheets Local Library."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tomllib
from typing import Mapping

DEFAULT_SPREADSHEET_ID = "1zH-9oPP_pBsq1Pxp0b5eNkniUlBj4DJYVcX13QnYAOA"
DEFAULT_WORKSHEET_NAME = "Local Library"
LOCAL_LIBRARY_SECRET_SECTION = "local_library"
GCP_SERVICE_ACCOUNT_SECRET_SECTION = "gcp_service_account"
_REPO_SECRETS_PATH = Path(".streamlit/secrets.toml")
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
    """Load Local Library config from Streamlit secrets, env vars, or a repo secrets file.

    Streamlit Cloud normally exposes values through ``st.secrets``.  For this app
    the repo may also carry ``.streamlit/secrets.toml`` intentionally, so the
    config loader accepts that file as a practical deployment source when
    Streamlit has not populated secrets yet.
    """

    if secrets is not None:
        return local_library_config_from_mapping(secrets)

    for candidate in (_streamlit_secrets(), _environment_secrets(), _repo_secrets_file()):
        config = local_library_config_from_mapping(candidate)
        if config.has_google_credentials:
            return config
    return local_library_config_from_mapping(_streamlit_secrets() or _environment_secrets() or _repo_secrets_file())


def local_library_config_from_mapping(secrets: Mapping[str, object] | None) -> LocalLibraryConfig:
    """Resolve config from a Streamlit-compatible secrets mapping."""

    if not secrets:
        return LocalLibraryConfig(missing_reason="Google Sheets connection settings are missing.")

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
            missing_reason="Google Sheets connection is incomplete: " + ", ".join(missing_keys),
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
        values = st.secrets  # type: ignore[assignment]
        return values if values else None
    except Exception:
        return None


def _environment_secrets() -> Mapping[str, object] | None:
    service_account = _service_account_from_env()
    if not service_account:
        return None
    library_section = {
        "spreadsheet_id": os.getenv("LOCAL_LIBRARY_SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID),
        "worksheet_name": os.getenv("LOCAL_LIBRARY_WORKSHEET_NAME", DEFAULT_WORKSHEET_NAME),
    }
    return {
        LOCAL_LIBRARY_SECRET_SECTION: library_section,
        GCP_SERVICE_ACCOUNT_SECRET_SECTION: service_account,
    }


def _service_account_from_env() -> Mapping[str, object] | None:
    raw_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, Mapping) else None

    env_values = {
        key: os.getenv("GCP_SERVICE_ACCOUNT_" + key.upper())
        for key in _REQUIRED_SERVICE_ACCOUNT_KEYS
    }
    if any(env_values.values()):
        return {key: value or "" for key, value in env_values.items()}
    return None


def _repo_secrets_file(path: Path = _REPO_SECRETS_PATH) -> Mapping[str, object] | None:
    try:
        if not path.exists():
            return None
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return parsed if isinstance(parsed, Mapping) else None


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
