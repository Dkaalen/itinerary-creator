"""Central test-suite groups used by the PowerShell test runners.

The project has grown enough that a raw ``pytest -q`` run can be hard to
interpret in short-lived environments.  Keeping the suite buckets here gives
patch work a stable, readable gate while preserving a true full-suite runner.
"""

from __future__ import annotations

from pathlib import Path

TEST_ROOT = "tests"
EMPTY_LEGACY_TEST_MODULES = frozenset({
    "test_images.py",
    "test_regressions.py",
    "test_regressions_rendering.py",
})
REMAINING_STAGE_SIZE = 8

FAST_TESTS = (
    "tests/test_time_text_helpers.py",
    "tests/test_date_formatting.py",
    "tests/test_date_resolver.py",
    "tests/test_render_cache.py",
    "tests/test_commercial_status_helpers.py",
    "tests/test_normalizer_context_architecture.py",
    "tests/test_transport_model_architecture.py",
    "tests/test_patch_ai_transport_domain.py",
    "tests/test_regressions_parser_normalizer.py",
    "tests/test_stress_logic_followups.py",
    "tests/test_itinerary_health_report.py",
    "tests/test_content_validator_scoping.py",
    "tests/test_fixture_quality_polish.py",
    "tests/test_nordic_quality_sample.py",
    "tests/test_compound_experience_transport_timing.py",
    "tests/test_accommodation_stress_fixtures.py",
    "tests/test_activity_compound_stress_fixtures.py",
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
    "tests/test_regressions_content_generation.py",
    "tests/test_regressions_transport_cruise.py",
    "tests/test_finland_transport_regressions.py",
    "tests/test_regressions_pdf_inclusions.py",
)

PDF_TESTS = (
    "tests/test_patch_aj_pdf_render_model.py",
    "tests/test_pdf.py",
    "tests/test_preview_pdf_parity.py",
    "tests/test_regressions_pdf_inclusions.py",
    "tests/test_rendered_pdf_quality.py",
    "tests/test_self_drive_pdf_preview_parity.py",
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
    "quality": QUALITY_TESTS,
    "pdf": PDF_TESTS,
    "slow": SLOW_TESTS,
}


def _module_name(path: str) -> str:
    return Path(path).name


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
        if stage_paths:
            stages.append((name, stage_paths))
            covered.update(_module_name(path) for path in stage_paths)

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

    for name, paths in (
        ("pdf/rendering", PDF_TESTS),
        ("slow quality", SLOW_TESTS),
    ):
        stage_paths = tuple(path for path in paths if _module_name(path) not in covered)
        if stage_paths:
            stages.append((name, stage_paths))
            covered.update(_module_name(path) for path in stage_paths)

    return tuple(stages)


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
