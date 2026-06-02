"""Shared pytest configuration for test-tier selection.

Test group membership lives in ``scripts.test_groups`` so the PowerShell
runners and pytest markers cannot silently drift apart.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.test_groups import (
    pdf_module_names,
    quality_module_names,
    slow_module_names,
)

PDF_MODULES = pdf_module_names()
SLOW_MODULES = slow_module_names()
QUALITY_MODULES = quality_module_names()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply coarse test markers by module name."""

    for item in items:
        module_name = Path(str(item.fspath)).name

        if module_name in PDF_MODULES:
            item.add_marker(pytest.mark.pdf)

        if module_name in SLOW_MODULES:
            item.add_marker(pytest.mark.slow)

        if module_name in QUALITY_MODULES:
            item.add_marker(pytest.mark.quality)
