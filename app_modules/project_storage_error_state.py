"""Application-state handling for project-storage failures."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.project_session_transitions import clear_failed_save, record_failed_save
from project_storage.errors import storage_error_detail, storage_user_message


def record_storage_error(
    state: MutableMapping[str, Any],
    exc: Exception,
    *,
    action: str = "storage",
) -> None:
    """Store user-safe and technical storage errors separately."""

    record_failed_save(
        state,
        user_message=storage_user_message(action),
        technical_detail=storage_error_detail(exc),
    )


def clear_storage_error(state: MutableMapping[str, Any]) -> None:
    """Clear the last storage failure markers."""

    clear_failed_save(state)
