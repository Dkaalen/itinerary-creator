"""Shared pytest configuration for test-tier selection.

The full itinerary suite contains a mix of tiny unit tests, parser regression
checks, PDF rendering checks, and real-fixture quality gates.  ChatGPT's patch
review environment has a short runtime limit, so these markers let us run a
stable fast suite after every patch while still keeping the full suite available
locally.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PDF_MODULES = {
    "test_pdf.py",
    "test_preview_pdf_parity.py",
    "test_regressions_pdf_inclusions.py",
    "test_rendered_pdf_quality.py",
    "test_self_drive_pdf_preview_parity.py",
}

SLOW_MODULES = {
    "test_broad_logic_stress_regressions.py",
    "test_pdf.py",
    "test_real_fixture_quality_gate.py",
    "test_regressions_fixture_quality.py",
    "test_rendered_pdf_quality.py",
    "test_self_drive_pdf_preview_parity.py",
}

QUALITY_MODULES = {
    "test_broad_logic_stress_regressions.py",
    "test_real_fixture_quality_gate.py",
    "test_regressions_fixture_quality.py",
    "test_rendered_pdf_quality.py",
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply coarse test markers by module name.

    Keeping this mapping centralized avoids editing dozens of test files and
    makes the fast/full test workflow easier to maintain.
    """

    for item in items:
        module_name = Path(str(item.fspath)).name

        if module_name in PDF_MODULES:
            item.add_marker(pytest.mark.pdf)

        if module_name in SLOW_MODULES:
            item.add_marker(pytest.mark.slow)

        if module_name in QUALITY_MODULES:
            item.add_marker(pytest.mark.quality)
