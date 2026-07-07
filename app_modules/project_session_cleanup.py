"""Project/session cleanup rules for cloud project boundaries."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.project_identity import clear_active_project_id
from app_modules.project_file_download_cache import clear_project_file_download_cache
from app_modules.workflow_transients import clear_project_boundary_transients

PROJECT_STORAGE_SESSION_KEYS: tuple[str, ...] = (
    "active_saved_project",
    "project_storage_last_saved_snapshot_path",
    "project_storage_last_calculator_file_path",
    "project_storage_last_calculator_snapshot",
    "project_storage_last_pdf_path",
    "project_storage_last_error",
    "project_storage_last_error_detail",
)

_CLOUD_CALCULATOR_PAYLOAD_PREFIX = "cloud_calculator_file_payload_"


def clear_cloud_project_download_payloads(state: MutableMapping[str, Any]) -> None:
    """Drop prepared cloud download bytes for the Open Project dialog."""

    for key in tuple(state.keys()):
        if str(key).startswith(_CLOUD_CALCULATOR_PAYLOAD_PREFIX):
            state.pop(key, None)


def clear_project_save_marker(state: MutableMapping[str, Any]) -> None:
    """Mark the current in-memory project as no longer cloud-saved."""

    state.pop("project_storage_last_saved_snapshot_path", None)


def clear_active_cloud_project_session(state: MutableMapping[str, Any]) -> None:
    """Clear cloud project identity, cached files, and browser transients."""

    for key in PROJECT_STORAGE_SESSION_KEYS:
        state.pop(key, None)
    clear_active_project_id(state)
    clear_cloud_project_download_payloads(state)
    clear_project_file_download_cache(state)
    clear_project_boundary_transients(state)


__all__ = [
    "PROJECT_STORAGE_SESSION_KEYS",
    "clear_active_cloud_project_session",
    "clear_cloud_project_download_payloads",
    "clear_project_save_marker",
]
