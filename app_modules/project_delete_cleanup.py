"""Cleanup active workflow state after a cloud project is deleted."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.project_browser_state import clear_file_delete_confirmation
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_session_cleanup import clear_active_cloud_project_session


def clear_deleted_project_from_session(state: MutableMapping[str, Any], project_id: str) -> None:
    """Clear active cloud/session caches when the deleted project is open."""

    if active_project_id_from_state(state) != str(project_id or "").strip():
        return
    clear_active_cloud_project_session(state)
    clear_file_delete_confirmation(state)
