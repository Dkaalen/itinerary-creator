"""Test-group data split out of scripts.test_groups.

Keep this package data-only; orchestration helpers stay in scripts.test_groups.
"""

from __future__ import annotations

TEST_ROOT = "tests"

EMPTY_LEGACY_TEST_MODULES = frozenset()

REMAINING_STAGE_SIZE = 8

TIERED_STAGE_SIZE = 4

PDF_STAGE_SIZE = 2

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
}
