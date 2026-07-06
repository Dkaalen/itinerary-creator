from __future__ import annotations

import json
from pathlib import Path

from calculator.library_config import (
    DEFAULT_SPREADSHEET_ID,
    DEFAULT_WORKSHEET_NAME,
    load_local_library_config,
)


_SERVICE_ACCOUNT = {
    "type": "service_account",
    "project_id": "project",
    "private_key_id": "key-id",
    "private_key": "private-key",
    "client_email": "service@example.com",
    "client_id": "client-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/service@example.com",
}


def test_local_library_config_reads_env_json(monkeypatch) -> None:
    monkeypatch.setenv("GCP_SERVICE_ACCOUNT_JSON", json.dumps(_SERVICE_ACCOUNT))

    config = load_local_library_config()

    assert config.has_google_credentials is True
    assert config.spreadsheet_id == DEFAULT_SPREADSHEET_ID
    assert config.worksheet_name == DEFAULT_WORKSHEET_NAME
    assert config.service_account_info["client_email"] == "service@example.com"


def test_local_library_config_accepts_mapping_without_warning_copy() -> None:
    config = load_local_library_config(
        {
            "local_library": {"spreadsheet_id": "sheet", "worksheet_name": "Library"},
            "gcp_service_account": _SERVICE_ACCOUNT,
        }
    )

    assert config.has_google_credentials is True
    assert config.spreadsheet_id == "sheet"
    assert config.worksheet_name == "Library"
