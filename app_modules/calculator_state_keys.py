"""Session-state keys owned by the calculator workflow."""

from __future__ import annotations

CALCULATOR_STATE_KEY = "calculator_state"
CALCULATOR_DRAFT_NAMESPACE_KEY = "calculator_draft_namespace"
CALCULATOR_ADVANCED_TOGGLE_KEY = "calculator_component_show_advanced"
CALCULATOR_READY_DOWNLOAD_KEY = "calculator_ready_xlsx_download"
CALCULATOR_ITINERARY_NAME_INPUT_KEY = "calculator_itinerary_name_input"
CALCULATOR_BACKUP_UPLOAD_KEY = "calculator_backup_upload"

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
