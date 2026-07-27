"""Test-group data split out of scripts.test_groups.

Keep this package data-only; orchestration helpers stay in scripts.test_groups.
"""

from __future__ import annotations

TEST_ROOT = "tests"

TEST_STAGE_BOUNDARY_SECONDS = 45

EMPTY_LEGACY_TEST_MODULES = frozenset()

REMAINING_STAGE_SIZE = 8

TIERED_STAGE_SIZE = 4

PDF_STAGE_SIZE = 2


# Modules whose complete pytest process exceeds the bounded stage window are
# expanded into isolated test-function targets by the runner. The catalogue
# still registers the module once, so coverage and ownership remain explicit.
BOUNDED_MODULE_TEST_SPLITS = {
    "tests/test_group_tour_rendering_regression.py": (
        "test_all_ten_sheets_render_one_canonical_block_per_package_day",
        "test_day_header_block_and_editor_share_the_same_contract",
        "test_final_inclusions_list_each_package_once_not_each_package_day",
        "test_package_accommodation_does_not_replace_pre_or_post_tour_hotels",
        "test_legacy_package_accommodation_is_not_recreated_as_hotel_products",
        "test_optional_and_commercial_items_never_become_package_inclusions",
        "test_preview_contains_one_package_and_ordered_daily_segments",
        "test_typed_pdf_uses_the_same_summer_and_winter_contract",
        "test_route_summary_and_season_are_package_owned",
        "test_season_conflict_remains_visible_without_cross_contaminating_rendering",
        "test_client_output_quality_accepts_all_ten_group_tour_sheets",
    ),
}

CHUNKED_GROUP_STAGE_SIZES = {
    "critical": 3,
    "fast": 6,
    # Parser fixture/idempotence modules can each take 20-30 seconds. Pairing
    # at most two modules keeps every stage inside the 45-second boundary.
    "parser": 2,
    "activity": 4,
    "architecture": 4,
    "calculator": 5,
    "editor": 4,
    "images": 4,
    "storage": 4,
    "ui": 4,
    "workflow": 4,
    # Pair quality modules to reduce interpreter/import startup while keeping
    # real-fixture and render-heavy checks in small timeout-safe stages.
    "quality": 2,
    "pdf": PDF_STAGE_SIZE,
    "calculator-browser": 1,
    "formulas": 2,
    "validation": 2,
    "workbook": 2,
    "calculator-realistic": 2,
    "project-management": 2,
    "rollback": 1,
    "cloud-lifecycle": 2,
    "reconstruction": 2,
    "generation": 2,
    "editor-pictures": 2,
    "generator": 2,
    "routes": 2,
    "inclusions": 2,
    "export": 2,
    "failure-modes": 2,
}
