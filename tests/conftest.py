"""Shared pytest configuration for marker discipline and Streamlit stubbing."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from support.streamlit_stub import install_streamlit_stub

from scripts.test_groups import (
    critical_module_names,
    fast_module_names,
    group_module_names,
    pdf_module_names,
    quality_module_names,
    slow_module_names,
)

GROUP_MODULES = group_module_names()
CRITICAL_MODULES = critical_module_names()
FAST_MODULES = fast_module_names()
PDF_MODULES = pdf_module_names()
SLOW_MODULES = slow_module_names()
QUALITY_MODULES = quality_module_names()
KNOWN_GROUPED_MODULES = set().union(*GROUP_MODULES.values())


def pytest_configure(config: pytest.Config) -> None:
    """Install the shared Streamlit stub before test modules are imported."""

    install_streamlit_stub()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply runner-group and coarse test markers by module name."""

    for item in items:
        module_name = Path(str(item.fspath)).name

        for group_name, module_names in GROUP_MODULES.items():
            if module_name in module_names:
                item.add_marker(getattr(pytest.mark, group_name))

        if module_name in QUALITY_MODULES:
            item.add_marker(pytest.mark.quality)

        if module_name in PDF_MODULES:
            item.add_marker(pytest.mark.pdf)

        if module_name in SLOW_MODULES:
            item.add_marker(pytest.mark.slow)

        if module_name in CRITICAL_MODULES or module_name in FAST_MODULES:
            item.add_marker(pytest.mark.unit)
        elif module_name in KNOWN_GROUPED_MODULES:
            item.add_marker(pytest.mark.integration)
