"""Focused bounded workflow test lanes."""
from __future__ import annotations

CALCULATOR_BROWSER_WORKFLOW_TESTS = (
    'tests/test_calculator_browser_editing_and_caret.py::test_arrow_keys_move_inside_text_only_while_cell_is_being_edited',
    'tests/test_calculator_browser_editing_and_caret.py::test_typing_pause_never_triggers_streamlit_sync_or_replaces_active_edit',
    'tests/test_calculator_browser_editing_and_caret.py::test_large_grid_text_typing_avoids_full_recalculation_and_per_key_draft_writes',
    'tests/test_calculator_browser_editing_and_caret.py::test_find_replace_and_selected_row_actions_work_in_the_rendered_grid',
    'tests/test_calculator_browser_editing_and_caret.py::test_row_insert_delete_and_column_resize_work_in_rendered_grid',
    'tests/test_calculator_browser_editing_and_caret.py::test_drag_fill_handle_copies_selected_cell_downward',
    'tests/test_calculator_browser_editing_and_caret.py::test_selected_day_cell_stays_compact_and_never_highlights_text',
    'tests/test_calculator_browser_editing_and_caret.py::test_formula_bar_and_selected_grid_cell_stay_in_sync',
    'tests/test_calculator_browser_navigation_and_focus.py::test_first_click_on_prefilled_cell_enables_immediate_arrow_navigation',
    'tests/test_calculator_browser_navigation_and_focus.py::test_selecting_prefilled_library_cell_does_not_open_suggestions_or_steal_arrows',
    'tests/test_calculator_browser_clipboard_and_paste.py::test_rectangular_paste_fill_and_undo_redo_behave_like_a_grid',
    'tests/test_calculator_browser_clipboard_and_paste.py::test_single_cell_copy_and_paste_work_in_grid_selection_mode',
    'tests/test_calculator_browser_clipboard_and_paste.py::test_paste_while_editing_inserts_plain_text_at_the_caret',
    'tests/test_calculator_browser_autocomplete_and_fetching.py::test_travel_element_autocomplete_stays_open_during_a_typing_pause',
    'tests/test_calculator_browser_autocomplete_and_fetching.py::test_fetched_suggestion_returns_focus_to_grid_navigation_mode',
    'tests/test_calculator_browser_autocomplete_and_fetching.py::test_fetched_nok_product_defaults_sales_price_to_eur_conversion',
    'tests/test_calculator_browser_formulas_and_currencies.py::test_cross_row_formula_dependents_refresh_immediately_after_edit',
    'tests/test_calculator_browser_formulas_and_currencies.py::test_sales_price_expression_is_precise_internally_and_shows_two_decimals',
    'tests/test_calculator_browser_formulas_and_currencies.py::test_sales_margin_shortcuts_target_actual_gp_after_commission_and_reset_to_automatic',
    'tests/test_calculator_browser_formulas_and_currencies.py::test_sales_margin_shortcut_uses_converted_gross_price',
    'tests/test_calculator_browser_download_and_import.py::test_explicit_download_submits_the_latest_unsynced_browser_state',
    'tests/test_calculator_browser_download_and_import.py::test_prepared_excel_downloads_from_the_grid_toolbar',
    'tests/test_calculator_browser_download_and_import.py::test_editing_after_excel_is_prepared_invalidates_the_stale_browser_download',
    'tests/test_calculator_browser_download_and_import.py::test_same_revision_backend_rerender_cannot_restore_a_stale_excel_download',
    'tests/test_calculator_browser_download_and_import.py::test_open_excel_sends_file_bytes_to_the_backend_action',
    'tests/test_calculator_browser_download_and_import.py::test_prepared_excel_auto_downloads_once_per_signature',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_currency_rate_rerender_keeps_the_unsynced_browser_draft',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_component_bridge_does_not_send_session_messages_before_first_render',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_open_project_requires_confirmation_before_replacing_current_work',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_backend_ack_clears_dirty_state_only_after_matching_request_is_accepted',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_rejected_stale_request_loads_new_backend_state_and_keeps_old_draft_recoverable',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_edits_made_after_submit_are_rebased_on_the_accepted_backend_revision',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_back_navigation_submits_invalid_financial_draft_without_blocking',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_generation_blocks_only_missing_itinerary_fields_with_row_feedback',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_generation_allows_financial_errors_when_itinerary_fields_are_complete',
    'tests/test_calculator_browser_component_lifecycle_and_messaging.py::test_transient_ack_keeps_invalid_browser_draft_on_same_backend_revision',
    'tests/test_calculator_browser_drafts_and_recovery.py::test_local_version_history_restores_an_earlier_calculator_state',
    'tests/test_calculator_browser_drafts_and_recovery.py::test_invalid_navigation_draft_restores_after_calculator_remount',
    'tests/test_calculator_browser_drafts_and_recovery.py::test_recovery_storage_uses_compact_hashes_and_row_deltas',
    'tests/test_calculator_browser_drafts_and_recovery.py::test_large_projects_adapt_retention_and_preserve_long_values',
    'tests/test_calculator_browser_drafts_and_recovery.py::test_quota_prunes_old_versions_before_current_draft',
    'tests/test_calculator_browser_drafts_and_recovery.py::test_unavailable_storage_shows_one_clear_warning',
    'tests/test_calculator_browser_drafts_and_recovery.py::test_legacy_recovery_arrays_remain_readable',
    'tests/test_calculator_component_protocol.py::test_protocol_accepts_matching_revision_and_acknowledges_applied_state',
    'tests/test_calculator_component_protocol.py::test_protocol_rejects_stale_rows_before_backend_state_is_mutated',
    'tests/test_calculator_component_protocol.py::test_protocol_treats_replayed_request_as_duplicate_without_new_action',
    'tests/test_calculator_component_protocol.py::test_protocol_bounds_processed_request_history',
    'tests/test_calculator_component_protocol.py::test_protocol_allows_matching_legacy_action_without_request_id',
)

FORMULA_WORKFLOW_TESTS = (
    "tests/test_calculator_cell_formulas.py",
    "tests/test_calculator_frontend_parity.py",
    "tests/test_calculator_financial_parity.py",
    "tests/test_calculator_formula_map.py",
)

VALIDATION_WORKFLOW_TESTS = (
    "tests/test_calculator_action_validation.py",
    "tests/test_calculator_validation.py",
    "tests/test_local_library_workbook_diagnostics.py",
)

WORKBOOK_WORKFLOW_TESTS = (
    "tests/test_calculator_workbook_export_plan.py",
    "tests/test_calculator_workbook_import.py",
    "tests/test_calculator_open_action.py",
    "tests/test_calculator_workbook_export.py",
    "tests/test_calculator_workbook_package_modules.py",
    "tests/test_calculator_template_structure.py",
)

REALISTIC_CALCULATOR_WORKFLOW_TESTS = (
    "tests/test_calculator_real_workflows.py",
    "tests/test_calculator_workflow_invariant.py",
)

PROJECT_MANAGEMENT_WORKFLOW_TESTS = (
    "tests/test_project_management.py",
    "tests/test_project_identity_state.py",
    "tests/test_current_edited_version_save_regression.py",
)

ROLLBACK_WORKFLOW_TESTS = (
    "tests/test_project_save_rollback.py",
)

CLOUD_LIFECYCLE_WORKFLOW_TESTS = (
    "tests/test_project_cloud_lifecycle_hardening.py",
    "tests/test_project_browser_and_downloads_regression.py",
)

RECONSTRUCTION_WORKFLOW_TESTS = (
    "tests/test_reconstruction_authorities.py",
    "tests/test_saved_project_rebuild_path_regression.py",
    "tests/test_saved_project_contract.py",
)

GENERATION_WORKFLOW_TESTS = (
    "tests/test_calculator_generation_action.py",
    "tests/test_hosted_workflow_guardrails_regression.py",
    "tests/test_generation_settings_and_preview_split.py",
)

EDITOR_PICTURES_WORKFLOW_TESTS = (
    "tests/test_add_pictures_workflow_regression.py",
    "tests/test_visual_editor_autosave_contract.py",
    "tests/test_editor_image_safety_regression.py",
)
