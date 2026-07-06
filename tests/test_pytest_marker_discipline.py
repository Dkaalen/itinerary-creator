from __future__ import annotations

import configparser
from pathlib import Path

from scripts.test_groups import GROUPS, fast_module_names, pdf_module_names, quality_module_names, slow_module_names

ROOT = Path(__file__).resolve().parents[1]


def _configured_marker_names() -> set[str]:
    parser = configparser.ConfigParser()
    parser.read(ROOT / "pytest.ini", encoding="utf-8")
    raw_markers = parser["pytest"]["markers"].splitlines()
    return {line.strip().split(":", 1)[0] for line in raw_markers if line.strip()}


def test_every_runner_group_has_a_declared_pytest_marker() -> None:
    configured = _configured_marker_names()

    assert set(GROUPS).issubset(configured)


def test_coarse_marker_names_are_declared() -> None:
    configured = _configured_marker_names()

    assert {"unit", "integration", "pdf", "quality", "slow"}.issubset(configured)


def test_fast_marker_scope_excludes_intentionally_heavy_lanes() -> None:
    heavy_modules = pdf_module_names() | quality_module_names() | slow_module_names()

    assert fast_module_names().isdisjoint(heavy_modules)
