"""Session-safe application actions for Project Explorer management."""

from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from typing import Any

from app_modules.project_browser_state import (
    bump_project_table_revision,
    clear_bulk_action,
    invalidate_folder_options,
    project_action_token_fingerprint,
    remember_selected_projects,
)
from app_modules.performance_telemetry import (
    measure_timing,
    new_operation_id,
    record_trace,
    telemetry_is_active,
)
from app_modules.project_identity import active_project_id_from_state
from app_modules.project_session_cleanup import clear_active_cloud_project_session
from app_modules.project_storage_service import (
    permanently_delete_cloud_projects,
    update_cloud_project_organization,
)
from app_modules.session_state_keys import (
    PROJECT_STORAGE_BROWSER_SUCCESS_KEY,
    PROJECT_STORAGE_BROWSER_WARNING_KEY,
)
from project_storage.project_results import ProjectBulkMutationResult


def apply_owner_change(
    state: MutableMapping[str, Any],
    project_ids: Sequence[str],
    *,
    owner_slug: str,
    actor_slug: str,
) -> bool:
    result = update_cloud_project_organization(
        tuple(project_ids), owner_slug=owner_slug, actor_slug=actor_slug
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
        tuple(project_ids), folder_name=folder_name, actor_slug=actor_slug
    )
    destination = folder_name or "No folder"
    return _complete_mutation(
        state,
        result,
        success_template=f"Moved {{count}} to {destination}.",
        invalidate_folders=True,
    )



def apply_delete_projects(
    state: MutableMapping[str, Any],
    project_ids: Sequence[str],
    *,
    confirmation_token: str = "",
) -> bool:
    """Permanently delete selected projects and preserve partial outcomes."""

    clean_ids = tuple(str(project_id or "").strip() for project_id in project_ids if str(project_id or "").strip())
    operation_id = new_operation_id("delete")
    telemetry_state = state if telemetry_is_active(state) else None
    if telemetry_state is not None:
        record_trace(
            telemetry_state,
            "project_delete_started",
            operation_id=operation_id,
            project_ids=clean_ids,
            project_count=len(clean_ids),
            confirmation_token_id=project_action_token_fingerprint(confirmation_token),
        )
    try:
        with measure_timing(
            telemetry_state,
            "project_delete_batch",
            count=len(clean_ids),
            note=operation_id,
        ):
            result = permanently_delete_cloud_projects(clean_ids)
    except Exception as exc:
        if telemetry_state is not None:
            record_trace(
                telemetry_state,
                "project_delete_failed",
                operation_id=operation_id,
                project_ids=clean_ids,
                error_type=type(exc).__name__,
                confirmation_token_id=project_action_token_fingerprint(confirmation_token),
            )
        raise
    if result is None:
        if telemetry_state is not None:
            record_trace(
                telemetry_state,
                "project_delete_completed",
                operation_id=operation_id,
                project_ids=clean_ids,
                outcome="storage_unavailable",
                confirmation_token_id=project_action_token_fingerprint(confirmation_token),
            )
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = (
            "Cloud storage is unavailable. No projects were deleted."
        )
        return False
    deleted_ids = result.deleted_ids
    if deleted_ids:
        state[PROJECT_STORAGE_BROWSER_SUCCESS_KEY] = f"Permanently deleted {_count_label(deleted_ids)}."
        _detach_active_project_if_affected(state, deleted_ids)
    if not result.complete:
        failed = len(result.incomplete_ids)
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = (
            f"{failed} selected project{'s' if failed != 1 else ''} could not be fully deleted. "
            "The retained records can be selected and retried."
        )
    if telemetry_state is not None:
        record_trace(
            telemetry_state,
            "project_delete_completed",
            operation_id=operation_id,
            project_ids=clean_ids,
            deleted_project_ids=result.deleted_ids,
            incomplete_project_ids=result.incomplete_ids,
            outcome="complete" if result.complete else "partial",
            confirmation_token_id=project_action_token_fingerprint(confirmation_token),
        )
    if result.complete:
        remember_selected_projects(state, ())
    else:
        remember_selected_projects(state, result.incomplete_ids)
    clear_bulk_action(state)
    bump_project_table_revision(state)
    invalidate_folder_options(state)
    return result.complete


def _complete_mutation(
    state: MutableMapping[str, Any],
    result: ProjectBulkMutationResult | None,
    *,
    success_template: str,
    invalidate_folders: bool,
) -> bool:
    if result is None:
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = (
            "Cloud storage is unavailable. No projects were changed."
        )
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
    if result.complete:
        remember_selected_projects(state, ())
    else:
        remember_selected_projects(state, result.missing_ids)
    clear_bulk_action(state)
    bump_project_table_revision(state)
    if invalidate_folders:
        invalidate_folder_options(state)
    return result.complete



def _detach_active_project_if_affected(
    state: MutableMapping[str, Any], project_ids: Sequence[str]
) -> None:
    active_id = active_project_id_from_state(state)
    if active_id and active_id in set(project_ids):
        clear_active_cloud_project_session(state)
        warning = (
            "The open project was deleted from cloud storage. "
            "Its current workspace remains available as unsaved work."
        )
        existing = str(state.get(PROJECT_STORAGE_BROWSER_WARNING_KEY) or "").strip()
        state[PROJECT_STORAGE_BROWSER_WARNING_KEY] = f"{existing} {warning}".strip()


def _count_label(project_ids: Sequence[str]) -> str:
    count = len(tuple(project_ids))
    return "1 project" if count == 1 else f"{count} projects"


__all__ = [
    "apply_delete_projects",
    "apply_folder_change",
    "apply_owner_change",
]
