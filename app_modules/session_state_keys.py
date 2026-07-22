"""Canonical cross-module Streamlit session-state keys and route values.

This module is intentionally dependency-free. Domain-specific modules may
re-export their owned keys for compatibility, but cross-workflow code should
import them from here instead of repeating raw strings.
"""

from __future__ import annotations

# Application routing and workflow stages.
ACTIVE_APP_PAGE_KEY = "active_app_page"
APP_STAGE_KEY = "app_stage"
WORKFLOW_PAGE = "workflow"
CALCULATOR_PAGE = "calculator"
LOCAL_LIBRARY_PAGE = "local_library"
WORKFLOW_STAGES = ("input", "edit", "pictures", "export")

# Core itinerary state shared by generation, editor, pictures, and export.
PARSED_ROWS_KEY = "parsed_rows"
OUTPUT_EDITS_KEY = "output_edits"
RAW_TEXT_INPUT_KEY = "raw_text_input"
LAST_GENERATED_RAW_TEXT_KEY = "last_generated_raw_text"
ITINERARY_HTML_KEY = "itinerary_html"
HTML_PATH_KEY = "html_path"
PREVIEW_SIGNATURE_KEY = "preview_signature"
ITINERARY_VALIDATION_REPORT_KEY = "itinerary_validation_report"
PARSER_DIAGNOSTICS_KEY = "parser_diagnostics"
STRUCTURED_INPUT_REVIEW_KEY = "structured_input_review"
ITINERARY_NAME_KEY = "itinerary_name"
ITINERARY_NAME_INPUT_KEY = "itinerary_name_input"
REQUESTED_OUTPUT_BRAND_KEY = "requested_output_brand"
PRESENTATION_LANGUAGE_KEY = "presentation_language"
REQUESTED_PRESENTATION_LANGUAGE_KEY = "requested_presentation_language"
TONE_PRESET_KEY = "tone_preset"
REQUESTED_TONE_PRESET_KEY = "requested_tone_preset"
DETAIL_LEVEL_KEY = "detail_level"
DAY_PAGE_LAYOUT_KEY = "day_page_layout"

# Active saved-project identity and persistence markers.
ACTIVE_SAVED_PROJECT_KEY = "active_saved_project"
ACTIVE_PROJECT_STORAGE_ID_KEY = "active_project_storage_id"
ACTIVE_SAVED_PROJECT_ID_KEY = "active_saved_project_id"
PROJECT_STORAGE_LAST_SAVED_SNAPSHOT_PATH_KEY = "project_storage_last_saved_snapshot_path"
PROJECT_STORAGE_LAST_CALCULATOR_FILE_PATH_KEY = "project_storage_last_calculator_file_path"
PROJECT_STORAGE_LAST_CALCULATOR_SNAPSHOT_KEY = "project_storage_last_calculator_snapshot"
PROJECT_STORAGE_LAST_PDF_PATH_KEY = "project_storage_last_pdf_path"
PROJECT_STORAGE_LAST_ERROR_KEY = "project_storage_last_error"
PROJECT_STORAGE_LAST_ERROR_DETAIL_KEY = "project_storage_last_error_detail"
PROJECT_STORAGE_BROWSER_SUCCESS_KEY = "project_storage_browser_success"
PROJECT_STORAGE_DELETE_CLEANUP_WARNING_KEY = "project_storage_delete_cleanup_warning"
OPEN_PROJECT_BROWSER_VISIBLE_KEY = "open_project_browser_visible"
OPEN_PROJECT_SEARCH_KEY = "open_project_search"
OPEN_PROJECT_SORT_KEY = "open_project_sort"
PENDING_PROJECT_BACKUP_IMPORT_KEY = "pending_project_backup_import"

__all__ = [name for name in globals() if name.isupper()]
