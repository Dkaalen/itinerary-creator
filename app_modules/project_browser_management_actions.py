"""Session-safe application actions for Project Explorer bulk management."""

from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from typing import Any

from app_modules.project_browser_state import (
    bump_project_table_revision,
    clear_bulk_action,
    invalidate_folder_options,
    remember_selected_project,
)
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_session_cleanup import clear_active_cloud_project_session
from app_modules.project_storage_service import (
    move_cloud_projects_to_trash,
    permanently_delete_cloud_projects,
    restore_cloud_projects_from_trash,
    update_cloud_project_organization,
)
from app_modules.session_state_keys import (
    PROJECT_STORAGE_BROWSER_SUCCESS_KEY,
    PROJECT_STORAGE_BROWSER_WARNING_KEY,
)
from project_storage.project_results import ProjectBulkMutationResult, ProjectBulkPurgeResult


def apply_owner_change(
    state: MutableMapping[str, Any],
    project_ids: Sequence[str],
    *,
    owner_slug: str,
    actor_slug: str,
) -> bool:
    result = update_cloud_project_organization(
        tuple(project_ids),
        owner_slug=owner_slug,
        actor_slug=actor_slug,
    )
    return _complete_mutation(
        state,
        result,
        success_template="Updated owner for {count}.",
        invalidate_folders=True,
    )


def apply_folder_change(
    state: MutableMapping[str, Any],
    project_ids: Sequence[str],
    *,
    folder_name: str,
    actor_slug: str,
) -> bool:
    result = update_cloud_project_organization(
        tuple(project_ids),
        folder_name=folder_name,
        actor_slug=actor_slug,
    )
    destination = folder_name or "No folder"
    return _complete_mutation(
        state,
        result,
        success_template=f"Moved {{count}} to {destination}.",
        invalidate_folders=True,
    )


def apply_move_to_trash(
    state: MutableMapping[str, Any],
    project_ids: Sequence[str],
    *,
    actor_slug: str,
) -> bool:
    result = move_cloud_projects_to_trash(tuple(project_ids), actor_slug=actor_slug)
    completed = _complete_mutation(
        state,
        result,
        success_template="Moved {count} to Trash.",
        invalidate_folders=True,
    )
    if result is not None:
        _detach_active_project_if_affected(state, result.affected_ids)
    return completed


def apply_restore_from_trash(
    state: MutableMapping[str, Any],
    project_ids: Sequence[str],
    *,
    actor_slug: str,
) -> bool:
    result = restore_cloud_projects_from_trash(tuple(project_ids), actor_slug=actor_slug)
    return _complete_mutation(
        state,
        result,
        success_template="Restored {count}.",
        invalidate_folders=True,
    )


def apply_permanent_purge(
    state: MutableMapping[str, Any],
    project_ids: Sequence[str],
) -> bool:
    result = permanently_delete_cloud_projects(tuple(project_ids))
    if result is None:
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = "Cloud storage is unavailable. No projects were deleted."
        return False
    deleted_ids = result.deleted_ids
    if deleted_ids:
        state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] = f"Permanently deleted {_count_label(deleted_ids)}."
        _detach_active_project_if_affected(state, deleted_ids)
    if not result.complete:
        failed = len(result.incomplete_ids)
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = (
            f"{failed} selected project{'s' if failed != 1 else ''} could not be fully deleted. "
            "They remain available for cleanup or retry when their database record was retained."
        )
    _finish_management_action(state, invalidate_folders=True)
    return result.complete


def _complete_mutation(
    state: MutableMapping[str, Any],
    result: ProjectBulkMutationResult | None,
    *,
    success_template: str,
    invalidate_folders: bool,
) -> bool:
    if result is None:
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = "Cloud storage is unavailable. No projects were changed."
        return False
    if result.affected_ids:
        state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] = success_template.format(
            count=_count_label(result.affected_ids)
        )
    if not result.complete:
        missed = len(result.missing_ids)
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = (
            f"{missed} selected project{'s' if missed != 1 else ''} could not be updated. "
            "Refresh the list and retry the remaining selection."
        )
    _finish_management_action(state, invalidate_folders=invalidate_folders)
    return result.complete


def _finish_management_action(state: MutableMapping[str, Any], *, invalidate_folders: bool) -> None:
    remember_selected_project(state, "")
    clear_bulk_action(state)
    bump_project_table_revision(state)
    if invalidate_folders:
        invalidate_folder_options(state)


def _detach_active_project_if_affected(state: MutableMapping[str, Any], project_ids: Sequence[str]) -> None:
    active_id = active_project_id_from_state(state)
    if active_id and active_id in set(project_ids):
        clear_active_cloud_project_session(state)
        warning = (
            "The open project was removed from cloud storage. Its current workspace remains available as unsaved work."
        )
        existing = str(state.get(PROJECT_STORAGE_BROWSER_WARNING_KEY) or "").strip()
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = f"{existing} {warning}".strip()


def _count_label(project_ids: Sequence[str]) -> str:
    count = len(tuple(project_ids))
    return "1 project" if count == 1 else f"{count} projects"


__all__ = [
    "apply_folder_change",
    "apply_move_to_trash",
    "apply_owner_change",
    "apply_permanent_purge",
    "apply_restore_from_trash",
]
