"""Clear transient workflow/browser state at hard project boundaries.

The app has several browser-backed workflows (visual editor, calculator grid,
image-bank discovery and PDF export).  Their pending nonces, caches and status
flags are useful within one active itinerary, but dangerous after a new
itinerary is generated or a saved project is reopened.  This module keeps that
cleanup contract in one place so project switches cannot resurrect stale
browser state on the hosted app.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.session_state_keys import PROJECT_SAVE_AS_NAME_KEY_PREFIX, PROJECT_SAVE_AS_VISIBLE_KEY

PROJECT_BOUNDARY_TRANSIENT_KEYS: tuple[str, ...] = (
    "parser_diagnostics",
    "structured_input_review",
    "image_bank_status",
    "image_bank_gateway",
    "_image_bank_status_cache",
    "image_bank_prefetch_started",
    "day_image_matches",
    "image_match_unmatched_days",
    "image_workflow_review",
    "image_review_warnings",
    "image_review_warning_count",
    "generation_duplicate_count",
    "generation_overflow_warnings",
    "add_pictures_last_error",
    "add_pictures_last_message",
    "export_last_error",
    "_last_visual_editor_result",
    "_visual_editor_commit_nonce",
    "_visual_editor_commit_counter",
    "_visual_editor_current_source_signature",
    "_visual_editor_last_applied_commit_nonce",
    "_visual_editor_last_result_changed",
    "_visual_editor_last_result_was_autosave",
    "_visual_editor_export_commit_ready",
    "_visual_editor_add_pictures_commit_ready",
    "_pdf_after_visual_edit_commit_nonce",
    "_pdf_after_visual_edit_commit_requested_at",
    "_add_pictures_after_visual_edit_commit_nonce",
    "_add_pictures_after_visual_edit_commit_requested_at",
    "_pdf_export_job",
    "_pdf_auto_create_requested",
    "_pdf_export_timings",
    "_performance_telemetry",
    "_project_file_download_cache",
    PROJECT_SAVE_AS_VISIBLE_KEY,
)


def clear_project_boundary_transients(state: MutableMapping[str, Any]) -> None:
    """Remove transient state that must not survive a project switch."""

    for key in PROJECT_BOUNDARY_TRANSIENT_KEYS:
        state.pop(key, None)
    for key in tuple(state):
        if str(key).startswith(PROJECT_SAVE_AS_NAME_KEY_PREFIX):
            state.pop(key, None)
