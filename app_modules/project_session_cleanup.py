"""Project/session cleanup rules for cloud project boundaries."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.calculator_state_keys import CALCULATOR_DRAFT_NAMESPACE_KEY
from app_modules.project_identity import clear_active_project_id
from app_modules.project_file_download_cache import clear_project_file_download_cache
from app_modules.workflow_transients import clear_project_boundary_transients
from app_modules.session_state_keys import (
    ACTIVE_SAVED_PROJECT_KEY,
    PROJECT_STORAGE_LAST_CALCULATOR_FILE_PATH_KEY,
    PROJECT_STORAGE_LAST_CALCULATOR_SNAPSHOT_KEY,
    PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY,
    PROJECT_STORAGE_LAST_ERROR_KEY,
    PROJECT_STORAGE_LAST_PDF_PATH_KEY,
    PROJECT_STORAGE_LAST_SAVED_SNAPSHOT_PATH_KEY,
)

PROJECT_STORAGE_PERSISTENCE_KEYS: tuple[str, ...] = (
    PROJECT_STORAGE_LAST_SAVED_SNAPSHOT_PATH_KEY,
    PROJECT_STORAGE_LAST_CALCULATOR_FILE_PATH_KEY,
    PROJECT_STORAGE_LAST_CALCULATOR_SNAPSHOT_KEY,
    PROJECT_STORAGE_LAST_PDF_PATH_KEY,
    PROJECT_STORAGE_LAST_ERROR_KEY,
    PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY,
)

PROJECT_STORAGE_SESSION_KEYS: tuple[str, ...] = (
    ACTIVE_SAVED_PROJECT_KEY,
    *PROJECT_STORAGE_PERSISTENCE_KEYS,
)

_CLOUD_CALCULATOR_PAYLOAD_PREFIX = "cloud_calculator_file_payload_"


def clear_cloud_project_download_payloads(state: MutableMapping[str, Any]) -> None:
    """Drop prepared cloud download bytes for the Open Project dialog."""

    for key in tuple(state.keys()):
        if str(key).startswith(_CLOUD_CALCULATOR_PAYLOAD_PREFIX):
            state.pop(key, None)


def clear_project_save_marker(state: MutableMapping[str, Any]) -> None:
    """Mark the current in-memory project as no longer cloud-saved."""

    state.pop(PROJECT_STORAGE_LAST_SAVED_SNAPSHOT_PATH_KEY, None)


def clear_cloud_project_persistence_markers(state: MutableMapping[str, Any]) -> None:
    """Detach the current in-memory project from prior cloud save/file markers."""

    for key in PROJECT_STORAGE_PERSISTENCE_KEYS:
        state.pop(key, None)
    state.pop(CALCULATOR_DRAFT_NAMESPACE_KEY, None)
    clear_cloud_project_download_payloads(state)
    clear_project_file_download_cache(state)


def clear_active_cloud_project_session(state: MutableMapping[str, Any]) -> None:
    """Clear cloud project identity, cached files, and browser transients."""

    for key in PROJECT_STORAGE_SESSION_KEYS:
        state.pop(key, None)
    clear_active_project_id(state)
    state.pop(CALCULATOR_DRAFT_NAMESPACE_KEY, None)
    clear_cloud_project_download_payloads(state)
    clear_project_file_download_cache(state)
    clear_project_boundary_transients(state)


__all__ = [
    "PROJECT_STORAGE_PERSISTENCE_KEYS",
    "PROJECT_STORAGE_SESSION_KEYS",
    "clear_active_cloud_project_session",
    "clear_cloud_project_persistence_markers",
    "clear_cloud_project_download_payloads",
    "clear_project_save_marker",
]
