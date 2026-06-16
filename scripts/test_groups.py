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

FAST_TESTS = (
    "tests/test_time_text_helpers.py",
    "tests/test_date_formatting.py",
    "tests/test_date_resolver.py",
    "tests/test_render_cache.py",
    "tests/test_commercial_status_helpers.py",
    "tests/test_normalizer_context_architecture.py",
    "tests/test_transport_model_architecture.py",
    "tests/test_patch_ai_transport_domain.py",
    "tests/test_patch_ak_cleanup_hygiene.py",
    "tests/test_patch_bz1f_dead_code_packaging.py",
    "tests/test_patch_al_editor_preview_ownership.py",
    "tests/test_patch_am_client_output_quality.py",
    "tests/test_patch_an_add_pictures_workflow.py",
    "tests/test_patch_bl_editor_styling.py",
    "tests/test_patch_bp_editor_workflow_split.py",
    "tests/test_patch_bq_style_registry.py",
    "tests/test_patch_bo_state_ownership.py",
    "tests/test_patch_bs_architecture_boundaries.py",
    "tests/test_regressions_parser_normalizer.py",
    "tests/test_patch_ih3_iceland_group_tour_parsing.py",
    "tests/test_stress_logic_followups.py",
    "tests/test_itinerary_health_report.py",
    "tests/test_content_validator_scoping.py",
    "tests/test_fixture_quality_polish.py",
    "tests/test_nordic_quality_sample.py",
    "tests/test_compound_experience_transport_timing.py",
    "tests/test_accommodation_stress_fixtures.py",
    "tests/test_activity_compound_stress_fixtures.py",
    "tests/test_patch_bx1_hot_path_caching.py",
    "tests/test_patch_by_destination_image_delivery.py",
    "tests/test_patch_bz1e_correctness_diagnostics.py",
    "tests/test_leisure_arrival_metadata_cleanup.py",
    "tests/test_patch_k_transport_preview_quality.py",
    "tests/test_messy_transport_safety_net.py",
    "tests/test_visual_editor_autosave_contract.py",
    "tests/test_visual_editor_typed_draft.py",
    "tests/test_patch_n_editor_image_safety.py",
    "tests/test_patch_o_editor_section_safety.py",
    "tests/test_structured_core_model.py",
    "tests/test_structured_html_source_identity.py",
    "tests/test_output_layout_contract.py",
    "tests/test_image_match_audit.py",
    "tests/test_patch_bt_nutshell_cover_toolbar.py",
    "tests/test_patch_bu_nutshell_fjordtours.py",
    "tests/test_patch_text_cleanup_caching.py",
)

PARSER_TESTS = (
    "tests/test_time_text_helpers.py",
    "tests/test_date_formatting.py",
    "tests/test_date_resolver.py",
    "tests/test_regressions_parser_normalizer.py",
    "tests/test_patch_ih3_iceland_group_tour_parsing.py",
    "tests/test_normalizer_context_architecture.py",
    "tests/test_patch_bf_parser_extractor_architecture.py",
    "tests/test_train_details.py",
    "tests/test_commercial_status_helpers.py",
    "tests/test_content_validator_scoping.py",
    "tests/test_patch_text_cleanup_caching.py",
)

ACTIVITY_TESTS = (
    "tests/test_activity_compound_stress_fixtures.py",
    "tests/test_activity_cruise_classification.py",
    "tests/test_compound_experience_transport_timing.py",
    "tests/test_content_classification_priority.py",
    "tests/test_product_rule_registry.py",
    "tests/test_patch_bc_activity_training_catalogue.py",
    "tests/test_patch_be_activity_product_architecture.py",
    "tests/test_patch_bg_activity_catalogue_and_qa.py",
    "tests/test_qg_c_source_fidelity.py",
    "tests/test_qg_d_norway_source_fidelity.py",
    "tests/test_qg_f_tallinn_excursion_wording.py",
    "tests/test_qg_g_activity_product_fingerprints.py",
    "tests/test_qg_h_activity_catalogue_hardening.py",
    "tests/test_qg_i_warning_ui_and_icebreaker_fidelity.py",
    "tests/test_patch_bx1_hot_path_caching.py",
    "tests/test_title_safety_phase1.py",
    "tests/test_patch_bt_nutshell_cover_toolbar.py",
    "tests/test_patch_bu_nutshell_fjordtours.py",
    "tests/test_patch_bz1a_nutshell_characterization.py",
    "tests/test_patch_bz1b_nutshell_domain.py",
    "tests/test_patch_bz1c_nutshell_consumer_parity.py",
    "tests/test_patch_bz1g_finland_source_fidelity.py",
    "tests/test_patch_ih1_reference_corpus.py",
    "tests/test_patch_ih2_group_tour_domain.py",
    "tests/test_patch_ih3_iceland_group_tour_parsing.py",
    "tests/test_patch_ih4_group_tour_rendering.py",
)

ARCHITECTURE_TESTS = (
    "tests/test_architecture_consolidation.py",
    "tests/test_patch_bz1f_dead_code_packaging.py",
    "tests/test_canonical_block_renderers.py",
    "tests/test_canonical_boundary.py",
    "tests/test_inclusion_exclusion_architecture.py",
    "tests/test_normalizer_context_architecture.py",
    "tests/test_output_layout_contract.py",
    "tests/test_quality_gate_architecture.py",
    "tests/test_render_document_source_of_truth.py",
    "tests/test_structured_core_model.py",
    "tests/test_structured_html_source_identity.py",
    "tests/test_transport_model_architecture.py",
    "tests/test_wrapper_exports.py",
    "tests/test_test_runner_groups.py",
    "tests/test_patch_bp_editor_workflow_split.py",
    "tests/test_patch_bq_style_registry.py",
    "tests/test_patch_bs_architecture_boundaries.py",
    "tests/test_patch_bt_nutshell_cover_toolbar.py",
    "tests/test_patch_bu_nutshell_fjordtours.py",
    "tests/test_patch_bz1a_nutshell_characterization.py",
    "tests/test_patch_bz1b_nutshell_domain.py",
    "tests/test_patch_bz1c_nutshell_consumer_parity.py",
    "tests/test_patch_bz1e_correctness_diagnostics.py",
    "tests/test_patch_bz1g_finland_source_fidelity.py",
    "tests/test_patch_ih1_reference_corpus.py",
    "tests/test_patch_ih2_group_tour_domain.py",
    "tests/test_patch_ih3_iceland_group_tour_parsing.py",
    "tests/test_patch_ih4_group_tour_rendering.py",
    "tests/test_patch_text_cleanup_caching.py",
    "tests/test_patch_text_cleanup_performance.py",
)

EDITOR_TESTS = (
    "tests/test_patch_al_editor_preview_ownership.py",
    "tests/test_patch_n_editor_image_safety.py",
    "tests/test_patch_o_editor_section_safety.py",
    "tests/test_patch_bl_editor_styling.py",
    "tests/test_patch_bp_editor_workflow_split.py",
    "tests/test_patch_bq_style_registry.py",
    "tests/test_patch_bo_state_ownership.py",
    "tests/test_qg_m_persistent_draft_autosave.py",
    "tests/test_structured_html_source_identity.py",
    "tests/test_visual_editor_autosave_contract.py",
    "tests/test_visual_editor_frontend_assets.py",
    "tests/test_visual_editor_typed_draft.py",
    "tests/test_patch_bt_nutshell_cover_toolbar.py",
    "tests/test_patch_bu_nutshell_fjordtours.py",
    "tests/test_patch_bz1c_nutshell_consumer_parity.py",
    "tests/test_patch_bz1g_finland_source_fidelity.py",
    "tests/test_patch_ih4_group_tour_rendering.py",
)

IMAGE_TESTS = (
    "tests/test_app_image_bank_paths.py",
    "tests/test_image_match_audit.py",
    "tests/test_image_matcher_selection.py",
    "tests/test_patch_bx1_hot_path_caching.py",
    "tests/test_patch_by_destination_image_delivery.py",
    "tests/test_patch_bz1d_image_bank_bootstrap.py",
    "tests/test_patch_an_add_pictures_workflow.py",
    "tests/test_patch_ap_output_quality_and_images.py",
    "tests/test_patch_ar_image_bank_enforcement.py",
    "tests/test_patch_au_remote_image_bank_connector.py",
    "tests/test_patch_aw_client_sanitizer_default_images.py",
    "tests/test_qg_k_picture_destination_accommodation.py",
    "tests/test_patch_bt_nutshell_cover_toolbar.py",
    "tests/test_patch_bu_nutshell_fjordtours.py",
)

UI_TESTS = (
    "tests/test_legacy_ui_cleanup.py",
    "tests/test_patch_bz1f_dead_code_packaging.py",
    "tests/test_regressions_ui_boundaries.py",
    "tests/test_ui_document_flow.py",
    "tests/test_ui_export_readiness.py",
    "tests/test_ui_image_bank_gateway.py",
    "tests/test_ui_pdf_download_persistence.py",
    "tests/test_ui_style_contrast.py",
    "tests/test_ui_workflow_shell.py",
    "tests/test_ui_workflow_state_actions.py",
    "tests/test_patch_bt_nutshell_cover_toolbar.py",
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
    "tests/test_patch_ao_output_quality_engine.py",
    "tests/test_patch_ap_output_quality_and_images.py",
    "tests/test_patch_aq_enforcement_gaps.py",
    "tests/test_patch_ar_image_bank_enforcement.py",
    "tests/test_patch_as_text_engine_consolidation.py",
    "tests/test_patch_at_reliability_diagnostics.py",
    "tests/test_patch_au_remote_image_bank_connector.py",
    "tests/test_patch_av_preview_pdf_group_tours.py",
    "tests/test_patch_aw_client_sanitizer_default_images.py",
    "tests/test_day_heading_dates.py",
    "tests/test_regressions_travel_text.py",
    "tests/test_patch_bz1e_correctness_diagnostics.py",
    "tests/test_patch_bz1g_finland_source_fidelity.py",
    "tests/test_patch_ih1_reference_corpus.py",
    "tests/test_patch_ih4_group_tour_rendering.py",
)

PDF_TESTS = (
    "tests/test_patch_aj_pdf_render_model.py",
    "tests/test_pdf.py",
    "tests/test_preview_pdf_parity.py",
    "tests/test_regressions_pdf_inclusions.py",
    "tests/test_rendered_pdf_quality.py",
    "tests/test_self_drive_pdf_preview_parity.py",
    "tests/test_patch_bt_nutshell_cover_toolbar.py",
    "tests/test_patch_bu_nutshell_fjordtours.py",
    "tests/test_patch_bz1c_nutshell_consumer_parity.py",
    "tests/test_patch_bz1e_correctness_diagnostics.py",
    "tests/test_patch_bz1g_finland_source_fidelity.py",
    "tests/test_patch_ih4_group_tour_rendering.py",
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
    "fast": FAST_TESTS,
    "parser": PARSER_TESTS,
    "activity": ACTIVITY_TESTS,
    "architecture": ARCHITECTURE_TESTS,
    "editor": EDITOR_TESTS,
    "images": IMAGE_TESTS,
    "ui": UI_TESTS,
    "quality": QUALITY_TESTS,
    "pdf": PDF_TESTS,
    "slow": SLOW_TESTS,
}

GROUP_ORDER = tuple(GROUPS)

GROUP_DESCRIPTIONS = {
    "fast": "small everyday safety gate for most patches",
    "parser": "text cleanup, date/time, extractor, and normalizer regressions",
    "activity": "activity product rules, catalogue matching, source fidelity, and QA warnings",
    "architecture": "structured model boundaries, render ownership, and test-runner infrastructure",
    "editor": "typed draft ownership, autosave, visual editor, and editor/PDF state safety",
    "images": "image-bank paths, matching, auditing, destination pictures, and image QA",
    "ui": "Streamlit workflow shell, export readiness, image gateway, and UI boundary tests",
    "quality": "medium itinerary quality and content/rendering regressions",
    "pdf": "PDF export and preview/PDF parity checks",
    "slow": "isolated large-fixture and PDF-heavy stability checks",
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
        "test_v36c53_optional_arc_transfer_quality_gate",
        "test_v36c55_clear_transport_wording_system",
        "test_v36c57_real_uploaded_inputs_quality_gate",
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
    """Return configured group paths that no longer exist."""

    configured = sorted({path for paths in GROUPS.values() for path in paths})
    return tuple(path for path in configured if not (repo_root / path).exists())



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
    if stage_paths:
        stages.append(("pdf/rendering", stage_paths))
        covered.update(_module_name(path) for path in stage_paths)

    slow_paths = tuple(path for path in SLOW_TESTS if _module_name(path) not in covered)
    for stage_name, stage_paths in build_slow_stages(slow_paths):
        stages.append((stage_name, stage_paths))
        covered.update(_module_name(path) for path in stage_paths)

    return tuple(stages)


def _expand_slow_targets(paths: tuple[str, ...]) -> tuple[str, ...]:
    targets: list[str] = []
    for path in paths:
        split_tests = SLOW_TEST_SPLITS.get(path)
        if split_tests:
            targets.extend(f"{path}::{test_name}" for test_name in split_tests)
        else:
            targets.append(path)
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

    return ("parser", "activity", "architecture", "editor", "images", "ui")


def group_descriptions() -> dict[str, str]:
    """Return human-readable descriptions for every named test lane."""

    return dict(GROUP_DESCRIPTIONS)


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
