"""Saved itinerary project schema constants."""

SAVED_PROJECT_SCHEMA_VERSION = 1
SAVED_PROJECT_KIND = "itinerary_project"
SAVED_PROJECT_MAX_BYTES = 2_000_000

ACTIVE_PROJECT_STATUS = "active"
ARCHIVED_PROJECT_STATUS = "archived"
SUPPORTED_PROJECT_STATUSES = frozenset({ACTIVE_PROJECT_STATUS, ARCHIVED_PROJECT_STATUS})

BANNED_SESSION_KEYS = frozenset(
    {
        "itinerary_html",
        "html_path",
        "pdf_bytes",
        "export_pdf_bytes",
        "preview_signature",
        "pdf_signature",
        "export_pdf_signature",
        "parser_diagnostics",
        "structured_input_review",
        "itinerary_validation_report",
        "image_bank_status",
        "image_bank_gateway",
        "image_bank_prefetch_started",
        "day_image_matches",
        "image_match_unmatched_days",
        "image_workflow_review",
        "image_review_warnings",
        "image_review_warning_count",
        "generation_duplicate_count",
        "generation_overflow_warnings",
        "export_last_error",
        "_preview_render_context",
        "_preview_render_context_signature",
        "_last_visual_editor_result",
        "_visual_editor_commit_nonce",
        "_visual_editor_commit_counter",
        "_visual_editor_last_applied_commit_nonce",
        "_visual_editor_export_commit_ready",
        "_visual_editor_add_pictures_commit_ready",
        "_pdf_after_visual_edit_commit_nonce",
        "_add_pictures_after_visual_edit_commit_nonce",
        "_pdf_export_job",
        "_pdf_auto_create_requested",
        "_pdf_export_timings",
        "_performance_telemetry",
        "_project_file_download_cache",
        "_pdf_image_contract_cache",
    }
)

BANNED_RECURSIVE_KEYS = frozenset(
    {
        "data_uri",
        "auto_data_uri",
        "preview_data_uri",
        "pending_preview",
        "preview_html",
        "html_preview",
        "itinerary_html",
        "pdf_bytes",
        "export_pdf_bytes",
        "base64",
        "b64",
        "browser_recovery_payload",
        "browser_recovery_draft",
        "local_draft",
        "local_draft_touched_keys",
        "autosave_payload",
    }
)
