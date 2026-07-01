"""Saved-project storage mode decision for the hosted app."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PROJECT_FILE_STORAGE_MODE = "project_file"
BROWSER_PRIVATE_BACKLOG_MODE = "browser_private_backlog"
CLOUD_BACKLOG_MODE = "cloud_backlog"


@dataclass(frozen=True)
class SavedProjectStorageDecision:
    """Describe the currently enabled saved-project storage behavior."""

    mode: str
    label: str
    user_summary: str
    backlog_enabled: bool = False
    browser_private_backlog_enabled: bool = False
    search_index_enabled: bool = False
    cloud_backend_enabled: bool = False
    future_cloud_backend_unblocked: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return a plain payload for tests and future UI/backend adapters."""

        return asdict(self)


CURRENT_SAVED_PROJECT_STORAGE = SavedProjectStorageDecision(
    mode=PROJECT_FILE_STORAGE_MODE,
    label="Project File mode",
    user_summary=(
        "Saved projects currently use project files: save a .itinerary.json file, "
        "then open that file later to continue editing."
    ),
)


BACKLOG_ACTIONS: tuple[str, ...] = ("open", "duplicate", "rename", "archive")
DEFERRED_BACKLOG_STORAGE_MODES: tuple[str, ...] = (
    BROWSER_PRIVATE_BACKLOG_MODE,
    CLOUD_BACKLOG_MODE,
)
FORBIDDEN_PROJECT_FILE_BACKLOG_KEYS: tuple[str, ...] = (
    "saved_project_backlog",
    "saved_projects_backlog",
    "saved_project_search_index",
    "saved_project_archive",
    "indexeddb_payload",
    "local_storage_payload",
)


def get_saved_project_storage_decision() -> SavedProjectStorageDecision:
    """Return the supported saved-project storage decision for this release."""

    return CURRENT_SAVED_PROJECT_STORAGE


def saved_project_backlog_is_enabled() -> bool:
    """Return whether the app should render a saved-itinerary backlog."""

    return get_saved_project_storage_decision().backlog_enabled


def enabled_backlog_actions() -> tuple[str, ...]:
    """Return active backlog actions for the current storage mode."""

    return BACKLOG_ACTIONS if saved_project_backlog_is_enabled() else ()


def assert_project_file_mode_payload(payload: dict[str, Any]) -> None:
    """Guard project-file payloads from accidental backlog/search-index storage."""

    text = str(payload).lower()
    for key in FORBIDDEN_PROJECT_FILE_BACKLOG_KEYS:
        if key.lower() in text:
            raise ValueError(f"Project-file payload must not include backlog storage field: {key}")
