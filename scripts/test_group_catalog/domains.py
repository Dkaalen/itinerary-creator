"""Independently runnable major-domain test lanes.

These lanes intentionally overlap focused implementation groups.  Duplicate
ownership across different lanes is allowed; duplicate target registration
inside one lane or one executable plan is not.
"""

GENERATOR_TESTS = (
    "tests/test_generation_architecture_cleanup.py",
    "tests/test_generation_settings_and_preview_split.py",
    "tests/test_itinerary_render_artifact_authority.py",
    "tests/test_render_document_source_of_truth.py",
    "tests/test_visual_editor_render_document_authority.py",
    "tests/test_calculator_generation_action.py",
    "tests/test_hosted_workflow_guardrails_regression.py",
    "tests/test_single_pipeline_brand_export_stability.py",
)

ROUTE_TESTS = (
    "tests/test_streamlit_routing_contract.py",
    "tests/test_lazy_page_imports.py",
    "tests/test_route_truth_precedence.py",
    "tests/test_transport_route_facts_authority.py",
    "tests/test_transport_model_architecture.py",
    "tests/test_destination_route_journey_intelligence.py",
    "tests/test_itinerary_continuity_contract.py",
)

INCLUSION_TESTS = (
    "tests/test_inclusion_exclusion_architecture.py",
    "tests/test_inclusions_preview_accommodation_transport_followups.py",
    "tests/test_regressions_pdf_inclusions.py",
    "tests/test_structured_core_model.py",
    "tests/test_structured_core_model_validation.py",
    "tests/test_structured_html_source_identity.py",
)

EXPORT_TESTS = (
    "tests/test_pdf_lazy_initialization_contract.py",
    "tests/test_pdf_export_canva_like_flow.py",
    "tests/test_pdf_export_fast_path.py",
    "tests/test_pdf_export_job_state.py",
    "tests/test_pdf_image_export_reliability.py",
    "tests/test_calculator_excel_export_integrity.py",
    "tests/test_calculator_workbook_export_plan.py",
    "tests/test_ui_export_readiness.py",
    "tests/test_client_readiness_export_gate_regression.py",
    "tests/test_single_pipeline_brand_export_stability.py",
)

FAILURE_MODE_TESTS = (
    "tests/test_failure_mode_regressions.py",
    "tests/test_loading_loop_recovery.py",
    "tests/test_editor_save_recovery_polish.py",
    "tests/test_visual_editor_frontend_recovery_contract.py",
    "tests/test_project_save_rollback.py",
    "tests/test_image_bank_bootstrap_rollback_regression.py",
    "tests/test_calculator_browser_recovery_storage_resilience.py",
    "tests/test_workflow_reliability_regression.py",
    "tests/test_saved_project_hardening_regression.py",
    "tests/test_reliability_diagnostics_regression.py",
)

__all__ = (
    "EXPORT_TESTS",
    "FAILURE_MODE_TESTS",
    "GENERATOR_TESTS",
    "INCLUSION_TESTS",
    "ROUTE_TESTS",
)
