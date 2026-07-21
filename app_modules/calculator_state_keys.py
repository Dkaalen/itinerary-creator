"""Session-state keys owned by the calculator workflow."""

from __future__ import annotations

CALCULATOR_STATE_KEY = "calculator_state"
CURRENCY_RATES_STATE_KEY = "calculator_currency_rates"
CALCULATOR_DRAFT_NAMESPACE_KEY = "calculator_draft_namespace"
CALCULATOR_ADVANCED_TOGGLE_KEY = "calculator_component_show_advanced"
CALCULATOR_READY_DOWNLOAD_KEY = "calculator_ready_xlsx_download"
CALCULATOR_ITINERARY_NAME_INPUT_KEY = "calculator_itinerary_name_input"
CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY = "calculator_itinerary_name_sync_required"
CALCULATOR_BACKUP_UPLOAD_KEY = "calculator_backup_upload"
CALCULATOR_NOTICE_KEY = "calculator_notice"
CALCULATOR_RETURN_AVAILABLE_KEY = "calculator_return_available"
CALCULATOR_COMPONENT_ACK_KEY = "calculator_component_ack"
CALCULATOR_PROCESSED_REQUEST_IDS_KEY = "calculator_processed_request_ids"
CALCULATOR_GENERATION_FEEDBACK_KEY = "calculator_generation_feedback"

# Retired Streamlit-data-editor/autocomplete keys.  They are cleared at hard
# project boundaries so old browser/session state cannot affect the custom grid.
LEGACY_CALCULATOR_SESSION_KEYS: tuple[str, ...] = (
    "calculator_show_advanced",
    "calculator_grid_revision",
    "calculator_selected_row_id",
    "calculator_travel_element_autocomplete_query",
    "calculator_travel_element_autocomplete_result_id",
)

LEGACY_CALCULATOR_SESSION_PREFIXES: tuple[str, ...] = (
    "calculator_grid_editor_",
)
