"""Central test-suite groups used by the PowerShell test runners.

The project has grown enough that a raw ``pytest -q`` run can be hard to
interpret in short-lived environments.  Keeping the suite buckets here gives
patch work a stable, readable gate while preserving a true full-suite runner.
"""

from __future__ import annotations

from pathlib import Path

TEST_ROOT = "tests"
EMPTY_LEGACY_TEST_MODULES = frozenset()
REMAINING_STAGE_SIZE = 8
TIERED_STAGE_SIZE = 4
PDF_STAGE_SIZE = 3
CHUNKED_GROUP_STAGE_SIZES = {
    "critical": 3,
    "fast": 6,
    "parser": 5,
    "activity": 4,
    "architecture": 4,
    "calculator": 5,
    "editor": 4,
    "images": 4,
    "storage": 4,
    "ui": 4,
    "workflow": 4,
    # Keep quality stages isolated: this lane contains several real-fixture
    # and render-quality modules that pass individually but can exceed hosted
    # subprocess time limits when bundled with neighbors.
    "quality": 1,
    "pdf": PDF_STAGE_SIZE,
}

CRITICAL_TESTS = (
    "tests/test_critical_feature_smoke.py",
    "tests/test_critical_workflow_contracts.py",
    "tests/test_failure_mode_regressions.py",
)

FAST_TESTS = (
    "tests/test_time_text_helpers.py",
    "tests/test_date_formatting.py",
    "tests/test_date_resolver.py",
    "tests/test_render_cache.py",
    "tests/test_commercial_status_helpers.py",
    "tests/test_normalizer_context_architecture.py",
    "tests/test_regressions_parser_normalizer.py",
    "tests/test_content_validator_scoping.py",
    "tests/test_leisure_arrival_metadata_cleanup.py",
    "tests/test_messy_transport_safety_net.py",
    "tests/test_structured_core_model.py",
    "tests/test_structured_html_source_identity.py",
    "tests/test_output_layout_contract.py",
    "tests/test_image_match_audit.py",
    "tests/test_text_cleanup_caching_regression.py",
    "tests/test_hot_path_caching_regression.py",
    "tests/test_destination_image_delivery_regression.py",
    "tests/test_fixture_quality_polish.py",
)

PARSER_TESTS = (
    "tests/test_output_qa1_client_risk_quality.py",
    "tests/test_time_text_helpers.py",
    "tests/test_date_formatting.py",
    "tests/test_date_resolver.py",
    "tests/test_regressions_parser_normalizer.py",
    "tests/test_iceland_group_tour_parsing_regression.py",
    "tests/test_normalizer_context_architecture.py",
    "tests/test_parser_extractor_architecture_regression.py",
    "tests/test_norway_coastal_cruise_transfer_regression.py",
    "tests/test_train_details.py",
    "tests/test_commercial_status_helpers.py",
    "tests/test_content_validator_scoping.py",
    "tests/test_text_cleanup_caching_regression.py",
    "tests/test_supplier_review_workflow_regression.py",
    "tests/test_supplier_correction_workflow_regression.py",
    "tests/test_accept_supplier_corrections_regression.py",
    "tests/test_copy1_premium_day_intro_engine.py",
)

ACTIVITY_TESTS = (
    "tests/test_activity_compound_stress_fixtures.py",
    "tests/test_activity_cruise_classification.py",
    "tests/test_compound_experience_transport_timing.py",
    "tests/test_content_classification_priority.py",
    "tests/test_product_rule_registry.py",
    "tests/test_activity_training_catalogue_regression.py",
    "tests/test_activity_product_architecture_regression.py",
    "tests/test_activity_catalogue_and_qa_regression.py",
    "tests/test_source_fidelity_quality_gate.py",
    "tests/test_norway_source_fidelity_quality_gate.py",
    "tests/test_tallinn_excursion_wording_quality_gate.py",
    "tests/test_activity_product_fingerprints_quality_gate.py",
    "tests/test_activity_catalogue_hardening_quality_gate.py",
    "tests/test_warning_ui_and_icebreaker_fidelity_quality_gate.py",
    "tests/test_hot_path_caching_regression.py",
    "tests/test_title_safety_phase1.py",
    "tests/test_nutshell_cover_toolbar_regression.py",
    "tests/test_nutshell_fjordtours_regression.py",
    "tests/test_nutshell_characterization_regression.py",
    "tests/test_nutshell_domain_regression.py",
    "tests/test_nutshell_consumer_parity_regression.py",
    "tests/test_finland_source_fidelity_regression.py",
    "tests/test_reference_corpus_regression.py",
    "tests/test_group_tour_domain_regression.py",
    "tests/test_iceland_group_tour_parsing_regression.py",
    "tests/test_group_tour_rendering_regression.py",
)

ARCHITECTURE_TESTS = (
    "tests/test_architecture_consolidation.py",
    "tests/test_foundation_cleanup_regression.py",
    "tests/test_architecture_guard_system.py",
    "tests/test_runtime_alignment.py",
    "tests/test_dead_code_packaging_regression.py",
    "tests/test_canonical_block_renderers.py",
    "tests/test_canonical_boundary.py",
    "tests/test_inclusion_exclusion_architecture.py",
    "tests/test_normalizer_context_architecture.py",
    "tests/test_output_layout_contract.py",
    "tests/test_quality_gate_architecture.py",
    "tests/test_render_document_source_of_truth.py",
    "tests/test_legacy_cleanup_regression_suite.py",
    "tests/test_structured_core_model.py",
    "tests/test_structured_html_source_identity.py",
    "tests/test_transport_model_architecture.py",
    "tests/test_wrapper_exports.py",
    "tests/test_destination_registry_regression.py",
    "tests/test_norway_destination_expansion_regression.py",
    "tests/test_sweden_destination_expansion_regression.py",
    "tests/test_finland_destination_expansion_regression.py",
    "tests/test_denmark_destination_expansion_regression.py",
    "tests/test_iceland_destination_expansion_regression.py",
    "tests/test_content1_destination_copy_library.py",
    "tests/test_destination_copy_profiles3_regression.py",
    "tests/test_destination_image_profiles_visual_consistency.py",
    "tests/test_destination_route_journey_intelligence.py",
    "tests/test_destination_qc_and_pagination_regression.py",
    "tests/test_compatibility_facade_audit.py",
    "tests/test_test_runner_groups.py",
    "tests/test_streamlit_style_authority.py",
    "tests/test_calculator_layout_regression.py",
    "tests/test_editor_workflow_split_regression.py",
    "tests/test_style_registry_regression.py",
    "tests/test_architecture_boundaries_regression.py",
    "tests/test_nutshell_cover_toolbar_regression.py",
    "tests/test_nutshell_fjordtours_regression.py",
    "tests/test_nutshell_characterization_regression.py",
    "tests/test_nutshell_domain_regression.py",
    "tests/test_nutshell_consumer_parity_regression.py",
    "tests/test_correctness_diagnostics_regression.py",
    "tests/test_finland_source_fidelity_regression.py",
    "tests/test_reference_corpus_regression.py",
    "tests/test_group_tour_domain_regression.py",
    "tests/test_iceland_group_tour_parsing_regression.py",
    "tests/test_group_tour_rendering_regression.py",
    "tests/test_text_cleanup_caching_regression.py",
    "tests/test_text_cleanup_performance_regression.py",
)

EDITOR_TESTS = (
    "tests/test_sync_regression_suite1.py",
    "tests/test_ready_for_client_workflow_regression.py",
    "tests/test_image_inspector_workflow_regression.py",
    "tests/test_editor_review_cleanup_contract.py",
    "tests/test_legacy_cleanup_regression_suite.py",
    "tests/test_actionable_review_center_regression.py",
    "tests/test_selection_refinement_regression.py",
    "tests/test_editor_preview_ownership_regression.py",
    "tests/test_editor_image_safety_regression.py",
    "tests/test_editor_section_safety_regression.py",
    "tests/test_editor_styling_regression.py",
    "tests/test_editor_workflow_split_regression.py",
    "tests/test_style_registry_regression.py",
    "tests/test_state_ownership_regression.py",
    "tests/test_persistent_draft_autosave_quality_gate.py",
    "tests/test_structured_html_source_identity.py",
    "tests/test_visual_editor_autosave_contract.py",
    "tests/test_visual_editor_frontend_assets.py",
    "tests/test_visual_editor_typed_draft.py",
    "tests/test_nutshell_cover_toolbar_regression.py",
    "tests/test_nutshell_fjordtours_regression.py",
    "tests/test_nutshell_consumer_parity_regression.py",
    "tests/test_finland_source_fidelity_regression.py",
    "tests/test_group_tour_rendering_regression.py",
    "tests/test_client_readiness_export_gate_regression.py",
)

IMAGE_TESTS = (
    "tests/test_app_image_bank_paths.py",
    "tests/test_image_bank_gateway_retry.py",
    "tests/test_image_match_audit.py",
    "tests/test_image_matcher_selection.py",
    "tests/test_hot_path_caching_regression.py",
    "tests/test_destination_image_delivery_regression.py",
    "tests/test_image_bank_bootstrap_regression.py",
    "tests/test_add_pictures_workflow_regression.py",
    "tests/test_output_quality_and_images_regression.py",
    "tests/test_image_bank_enforcement_regression.py",
    "tests/test_remote_image_bank_connector_regression.py",
    "tests/test_client_sanitizer_default_images_regression.py",
    "tests/test_picture_destination_accommodation_quality_gate.py",
    "tests/test_nutshell_cover_toolbar_regression.py",
    "tests/test_nutshell_fjordtours_regression.py",
    "tests/test_southern_coastal_image_season_policy.py",
    "tests/test_destination_registry_regression.py",
    "tests/test_norway_destination_expansion_regression.py",
    "tests/test_sweden_destination_expansion_regression.py",
    "tests/test_finland_destination_expansion_regression.py",
    "tests/test_denmark_destination_expansion_regression.py",
    "tests/test_iceland_destination_expansion_regression.py",
    "tests/test_content1_destination_copy_library.py",
    "tests/test_destination_copy_profiles3_regression.py",
    "tests/test_destination_image_profiles_visual_consistency.py",
    "tests/test_destination_route_journey_intelligence.py",
    "tests/test_destination_qc_and_pagination_regression.py",
    "tests/test_image_qa1_service_aware_matching.py",
    "tests/test_itinerary_wide_image_assignment.py",
)

UI_TESTS = (
    "tests/test_sync_regression_suite1.py",
    "tests/test_output_qa1_client_risk_quality.py",
    "tests/test_ready_for_client_workflow_regression.py",
    "tests/test_image_inspector_workflow_regression.py",
    "tests/test_editor_review_cleanup_contract.py",
    "tests/test_actionable_review_center_regression.py",
    "tests/test_selection_refinement_regression.py",
    "tests/test_legacy_ui_cleanup.py",
    "tests/test_dead_code_packaging_regression.py",
    "tests/test_regressions_ui_boundaries.py",
    "tests/test_ui_document_flow.py",
    "tests/test_ui_export_readiness.py",
    "tests/test_legacy_cleanup_regression_suite.py",
    "tests/test_ui_image_bank_gateway.py",
    "tests/test_ui_pdf_download_persistence.py",
    "tests/test_project_browser_and_downloads_regression.py",
    "tests/test_project_browser_state.py",
    "tests/test_ui_style_contrast.py",
    "tests/test_calculator_layout_regression.py",
    "tests/test_ui_workflow_shell.py",
    "tests/test_ui_workflow_state_actions.py",
    "tests/test_nutshell_cover_toolbar_regression.py",
    "tests/test_editor_workspace_polish.py",
    "tests/test_editor_interaction_polish.py",
    "tests/test_supplier_review_workflow_regression.py",
    "tests/test_supplier_correction_workflow_regression.py",
    "tests/test_accept_supplier_corrections_regression.py",
    "tests/test_premium_output_regression_followup.py",
    "tests/test_destination_image_profiles_visual_consistency.py",
    "tests/test_destination_route_journey_intelligence.py",
    "tests/test_destination_qc_and_pagination_regression.py",
    "tests/test_copy1_premium_day_intro_engine.py",
    "tests/test_client_readiness_export_gate_regression.py",
    "tests/test_brand1_proposal_profiles.py",
)

DAY_BRAIN_TESTS = (
    "tests/test_day_brain_copy.py",
    "tests/test_day_brain_intelligence.py",
    "tests/test_day_brain_proof_hardening.py",
    "tests/test_day_sub_brains.py",
)

QUALITY_TESTS = (
    "tests/test_accommodation_wording.py",
    "tests/test_content_classification_priority.py",
    "tests/test_product_rule_registry.py",
    "tests/test_canonical_block_renderers.py",
    "tests/test_canonical_boundary.py",
    "tests/test_render_document_source_of_truth.py",
    "tests/test_inclusions_preview_accommodation_transport_followups.py",
    "tests/test_inclusion_exclusion_architecture.py",
    "tests/test_quality_gate_architecture.py",
    "tests/test_premium_optional_output.py",
    "tests/test_regressions_content_basics.py",
    "tests/test_regressions_transport_cruise.py",
    "tests/test_finland_transport_regressions.py",
    "tests/test_regressions_pdf_inclusions.py",
    "tests/test_output_quality_engine_regression.py",
    "tests/test_output_quality_and_images_regression.py",
    "tests/test_enforcement_gaps_regression.py",
    *DAY_BRAIN_TESTS,
    "tests/test_image_bank_enforcement_regression.py",
    "tests/test_text_engine_consolidation_regression.py",
    "tests/test_reliability_diagnostics_regression.py",
    "tests/test_remote_image_bank_connector_regression.py",
    "tests/test_preview_pdf_group_tours_regression.py",
    "tests/test_client_sanitizer_default_images_regression.py",
    "tests/test_day_heading_dates.py",
    "tests/test_regressions_travel_text.py",
    "tests/test_correctness_diagnostics_regression.py",
    "tests/test_finland_source_fidelity_regression.py",
    "tests/test_reference_corpus_regression.py",
    "tests/test_group_tour_rendering_regression.py",
    "tests/test_content1_destination_copy_library.py",
    "tests/test_destination_copy_profiles3_regression.py",
    "tests/test_vipin_full_corpus_fixture.py",
    "tests/test_destination_route_journey_intelligence.py",
    "tests/test_destination_qc_and_pagination_regression.py",
)

PDF_TESTS = (
    "tests/test_sync_regression_suite1.py",
    "tests/test_pdf_render_model_regression.py",
    "tests/test_pdf6_luxury_proposal.py",
    "tests/test_pdf7_proposal_footer.py",
    "tests/test_pdf_export_fast_path.py",
    "tests/test_pdf_image_export_reliability.py",
    "tests/test_pdf_creation_flow_and_layout_cleanup.py",
    "tests/test_preview_pdf_parity.py",
    "tests/test_regressions_pdf_inclusions.py",
    "tests/test_nutshell_cover_toolbar_regression.py",
    "tests/test_nutshell_fjordtours_regression.py",
    "tests/test_nutshell_consumer_parity_regression.py",
    "tests/test_correctness_diagnostics_regression.py",
    "tests/test_finland_source_fidelity_regression.py",
    "tests/test_group_tour_rendering_regression.py",
    "tests/test_premium_output_upgrade.py",
    "tests/test_premium_output_regression_followup.py",
    "tests/test_destination_image_profiles_visual_consistency.py",
    "tests/test_destination_route_journey_intelligence.py",
    "tests/test_destination_qc_and_pagination_regression.py",
    "tests/test_pdf8_luxury_day_layout.py",
    "tests/test_destination_copy_profiles3_regression.py",
    "tests/test_brand1_proposal_profiles.py",
)


CALCULATOR_TESTS = (
    "tests/test_calculator_backup_action.py",
    "tests/test_calculator_calculations.py",
    "tests/test_calculator_cleanup_state.py",
    "tests/test_calculator_component_mounting.py",
    "tests/test_calculator_component_payload.py",
    "tests/test_calculator_component_result.py",
    "tests/test_calculator_download_staleness.py",
    "tests/test_calculator_fetch_lines.py",
    "tests/test_calculator_formula_map.py",
    "tests/test_calculator_generation_action.py",
    "tests/test_calculator_grid_autocomplete.py",
    "tests/test_calculator_grid_values.py",
    "tests/test_calculator_library_cache.py",
    "tests/test_calculator_library_read_summary.py",
    "tests/test_calculator_library_search.py",
    "tests/test_calculator_library_seed_import.py",
    "tests/test_calculator_library_store.py",
    "tests/test_calculator_numeric_input.py",
    "tests/test_calculator_row_model.py",
    "tests/test_calculator_session_state.py",
    "tests/test_calculator_state.py",
    "tests/test_calculator_state_serialization.py",
    "tests/test_calculator_template_structure.py",
    "tests/test_calculator_to_itinerary_input.py",
    "tests/test_calculator_ui_foundation.py",
    "tests/test_calculator_layout_regression.py",
    "tests/test_calculator_workbook_export.py",
)

STORAGE_TESTS = (
    "tests/test_project_identity_state.py",
    "tests/test_project_storage_file_writer.py",
    "tests/test_project_storage_foundation.py",
    "tests/test_project_file_mvp_regression.py",
    "tests/test_current_edited_version_save_regression.py",
    "tests/test_saved_project_hardening_regression.py",
    "tests/test_project_browser_and_downloads_regression.py",
    "tests/test_project_browser_state.py",
    "tests/test_project_cloud_lifecycle_hardening.py",
)

WORKFLOW_TESTS = (
    "tests/test_workflow_reliability_regression.py",
    "tests/test_hosted_workflow_guardrails_regression.py",
    "tests/test_ui_workflow_shell.py",
    "tests/test_ui_workflow_state_actions.py",
    "tests/test_ui_export_readiness.py",
    "tests/test_ui_pdf_download_persistence.py",
    "tests/test_project_browser_and_downloads_regression.py",
    "tests/test_client_readiness_export_gate_regression.py",
    "tests/test_visual_editor_autosave_contract.py",
    "tests/test_visual_editor_typed_draft.py",
)

SLOW_TESTS = (
    "tests/test_broad_logic_stress_regressions.py",
    "tests/test_pdf.py",
    "tests/test_real_fixture_quality_gate.py",
    "tests/test_regressions_fixture_quality.py",
    "tests/test_rendered_pdf_quality.py",
    "tests/test_self_drive_pdf_preview_parity.py",
)

GROUPS = {
    "critical": CRITICAL_TESTS,
    "fast": FAST_TESTS,
    "parser": PARSER_TESTS,
    "activity": ACTIVITY_TESTS,
    "architecture": ARCHITECTURE_TESTS,
    "calculator": CALCULATOR_TESTS,
    "editor": EDITOR_TESTS,
    "images": IMAGE_TESTS,
    "storage": STORAGE_TESTS,
    "ui": UI_TESTS,
    "workflow": WORKFLOW_TESTS,
    "quality": QUALITY_TESTS,
    "pdf": PDF_TESTS,
    "slow": SLOW_TESTS,
}

GROUP_ORDER = tuple(GROUPS)

# Short, timeout-safe confidence paths.  These are intentionally explicit so
# CI, PowerShell runners, and release validation cannot silently drift apart.
HEALTH_CHECK_GROUPS = ("critical",)
RELEASE_CANDIDATE_GROUPS = (
    "critical",
    "fast",
    "calculator",
    "storage",
    "workflow",
    "parser",
    "activity",
    "architecture",
    "editor",
    "images",
    "ui",
    "quality",
    "pdf",
)
CI_MATRIX_GROUPS = (
    "critical",
    "fast",
    "calculator",
    "storage",
    "workflow",
    "architecture",
    "parser",
    "activity",
    "editor",
    "images",
    "ui",
)

GROUP_DESCRIPTIONS = {
    "critical": "instant smoke/contracts for critical app surfaces and known failure classes",
    "fast": "small everyday safety gate with PDF/slow/large quality checks excluded",
    "parser": "text cleanup, date/time, extractor, and normalizer regressions",
    "activity": "activity product rules, catalogue matching, source fidelity, and QA warnings",
    "architecture": "structured model boundaries, render ownership, and test-runner infrastructure",
    "calculator": "calculator state, grid payloads, local library, and workbook export",
    "editor": "typed draft ownership, autosave, visual editor, and editor/PDF state safety",
    "images": "image-bank paths, matching, auditing, destination pictures, and image QA",
    "storage": "project identity, Supabase repository, file save/load, and cloud browser behavior",
    "ui": "Streamlit workflow shell, export readiness, image gateway, and UI boundary tests",
    "workflow": "hosted app flow, stage transitions, editor/export state, and runtime guardrails",
    "quality": "medium itinerary quality and content/rendering regressions",
    "pdf": "PDF export and preview/PDF parity checks",
    "slow": "isolated large-fixture and PDF-heavy stability checks",
    "health": "instant local health check: compile/import plus the critical smoke lane",
    "release": "strong timeout-safe release candidate check without the isolated slow harness",
}

SLOW_TEST_SPLITS = {
    "tests/test_regressions_fixture_quality.py": (
        "test_content_cleanup_for_helsinki_lapland_sample",
        "test_bad_input_contextual_travel_and_activity_cleanup",
        "test_korouoma_priority_keeps_thermal_and_barbecue",
        "test_self_guided_tallinn_is_not_labeled_guided",
        "test_generalized_iceland_self_drive_logic",
        "test_real_input_fixture_bank_core_expectations",
        "test_sweden_lapland_supplier_booking_information_not_in_client_inclusions",
        "test_optional_arc_transfer_quality_gate",
        "test_clear_transport_wording_system",
        "test_real_uploaded_inputs_quality_gate",
    ),
}


def _module_name(path: str) -> str:
    module_path = str(path).partition("::")[0]
    return Path(module_path).name


def existing_test_modules(repo_root: Path) -> tuple[str, ...]:
    """Return first-party pytest modules that currently contain active tests."""

    tests_dir = repo_root / TEST_ROOT
    return tuple(
        path.name
        for path in sorted(tests_dir.glob("test_*.py"))
        if path.name not in EMPTY_LEGACY_TEST_MODULES
    )


def empty_legacy_test_modules() -> frozenset[str]:
    """Return placeholder modules that are intentionally skipped by grouped runs."""

    return EMPTY_LEGACY_TEST_MODULES


def missing_group_paths(repo_root: Path) -> tuple[str, ...]:
    """Return configured group paths that no longer exist.

    Group entries may be either modules or explicit pytest node ids. Only the
    file portion should be checked on disk.
    """

    configured = sorted({path for paths in GROUPS.values() for path in paths})
    return tuple(path for path in configured if not (repo_root / path.partition("::")[0]).exists())



def chunked_group_stages(
    stage_prefix: str,
    paths: tuple[str, ...],
    stage_size: int = TIERED_STAGE_SIZE,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Split larger named lanes into readable, timeout-friendly stages."""

    if not paths:
        return ()

    chunks = tuple(
        paths[index : index + stage_size]
        for index in range(0, len(paths), stage_size)
    )
    if len(chunks) == 1:
        return ((stage_prefix, chunks[0]),)
    return tuple(
        (f"{stage_prefix} {index}/{len(chunks)}", chunk)
        for index, chunk in enumerate(chunks, start=1)
    )

def remaining_test_paths(
    repo_root: Path,
    already_covered: set[str] | None = None,
    reserved_for_later: set[str] | None = None,
) -> tuple[str, ...]:
    """Return test modules not covered by the named runner groups yet."""

    covered = set(already_covered or set())
    reserved = set(reserved_for_later or set())
    return tuple(
        f"{TEST_ROOT}/{module}"
        for module in existing_test_modules(repo_root)
        if module not in covered and module not in reserved
    )


def build_full_stages(repo_root: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Build a no-duplicate full-suite plan with readable progress stages."""

    stages: list[tuple[str, tuple[str, ...]]] = []
    covered: set[str] = set()

    for name, paths in (
        ("fast safety", FAST_TESTS),
        ("quality", QUALITY_TESTS),
    ):
        stage_paths = tuple(path for path in paths if _module_name(path) not in covered)
        for stage_name, chunk in chunked_group_stages(name, stage_paths):
            stages.append((stage_name, chunk))
            covered.update(_module_name(path) for path in chunk)

    reserved_for_later = {
        _module_name(path)
        for path in (*PDF_TESTS, *SLOW_TESTS)
        if _module_name(path) not in covered
    }
    remaining = remaining_test_paths(repo_root, covered, reserved_for_later)
    if remaining:
        chunks = tuple(
            remaining[index : index + REMAINING_STAGE_SIZE]
            for index in range(0, len(remaining), REMAINING_STAGE_SIZE)
        )
        for index, chunk in enumerate(chunks, start=1):
            stages.append((f"remaining non-tiered {index}/{len(chunks)}", chunk))
            covered.update(_module_name(path) for path in chunk)

    stage_paths = tuple(path for path in PDF_TESTS if _module_name(path) not in covered)
    for stage_name, chunk in chunked_group_stages("pdf/rendering", stage_paths, stage_size=PDF_STAGE_SIZE):
        stages.append((stage_name, chunk))
        covered.update(_module_name(path) for path in chunk)

    slow_paths = tuple(path for path in SLOW_TESTS if _module_name(path) not in covered)
    for stage_name, stage_paths in build_slow_stages(slow_paths):
        stages.append((stage_name, stage_paths))
        covered.update(_module_name(path) for path in stage_paths)

    return tuple(stages)


def _expand_slow_targets(paths: tuple[str, ...]) -> tuple[str, ...]:
    if tuple(paths) == SLOW_TESTS:
        return slow_direct_targets()

    root = Path(__file__).resolve().parents[1]
    targets: list[str] = []
    for path in paths:
        explicit_tests = SLOW_TEST_SPLITS.get(path)
        names = explicit_tests or _no_arg_test_function_names(root, path)
        targets.extend(f"{path}::{test_name}" for test_name in names)
    return tuple(targets)


def _target_label(target: str) -> str:
    module, _, test_name = target.partition("::")
    if test_name:
        return f"{_module_name(module)}::{test_name}"
    return _module_name(module)


def build_slow_stages(
    paths: tuple[str, ...] | None = None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Run slow targets in isolated pytest subprocesses to avoid global state leaks."""

    selected_targets = _expand_slow_targets(tuple(paths or SLOW_TESTS))
    return tuple(
        (f"slow {index}/{len(selected_targets)}: {_target_label(target)}", (target,))
        for index, target in enumerate(selected_targets, start=1)
    )


def focused_group_names() -> tuple[str, ...]:
    """Return non-tiered convenience lanes for targeted patch validation."""

    return ("critical", "parser", "activity", "architecture", "calculator", "editor", "images", "storage", "ui", "workflow")


def group_descriptions() -> dict[str, str]:
    """Return human-readable descriptions for every named test lane."""

    return dict(GROUP_DESCRIPTIONS)




def group_module_names() -> dict[str, set[str]]:
    """Return test module names keyed by runner group."""

    return {name: {_module_name(path) for path in paths} for name, paths in GROUPS.items()}


def module_group_names(module_name: str) -> tuple[str, ...]:
    """Return runner groups that include a test module."""

    groups = group_module_names()
    return tuple(name for name in GROUP_ORDER if module_name in groups[name])


def critical_module_names() -> set[str]:
    return {_module_name(path) for path in CRITICAL_TESTS}


def fast_module_names() -> set[str]:
    return {_module_name(path) for path in FAST_TESTS}


def _no_arg_test_function_names(repo_root: Path, relative_path: str) -> tuple[str, ...]:
    """Return direct-callable no-fixture test functions from a test module."""

    import ast

    tree = ast.parse((repo_root / relative_path).read_text(encoding="utf-8"))
    names = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
        and not node.args.args
    ]
    return tuple(names)


def slow_direct_targets(repo_root: Path | None = None) -> tuple[str, ...]:
    """Return the exact isolated slow-test targets used by the slow harness."""

    root = repo_root or Path(__file__).resolve().parents[1]
    targets: list[str] = []
    for path in SLOW_TESTS:
        explicit_tests = SLOW_TEST_SPLITS.get(path)
        names = explicit_tests or _no_arg_test_function_names(root, path)
        targets.extend(f"{path}::{name}" for name in names)
    return tuple(targets)


def pdf_module_names() -> set[str]:
    return {_module_name(path) for path in PDF_TESTS}


def slow_module_names() -> set[str]:
    return {_module_name(path) for path in SLOW_TESTS}


def quality_module_names() -> set[str]:
    return {_module_name(path) for path in QUALITY_TESTS} | {
        "test_broad_logic_stress_regressions.py",
        "test_real_fixture_quality_gate.py",
        "test_regressions_fixture_quality.py",
        "test_rendered_pdf_quality.py",
    }
