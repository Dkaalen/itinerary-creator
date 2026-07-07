"""Broad performance gates for the text-cleanup workflow cache."""

from __future__ import annotations

from pathlib import Path

from scripts.benchmark_text_cleanup import run_benchmark
from text_polish_modules.text_cleanup import polish_client_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_representative_workflow_reuses_cleanup_results_without_output_drift() -> None:
    result = run_benchmark(
        PROJECT_ROOT,
        fixture_names=("finland_winter_quality_check.txt",),
        repeats=1,
        include_pdf=False,
    )

    assert result["warm_output_identical"] is True
    assert result["cache_after_warm"]["fix_common_text"]["hits"] > 0
    assert result["cache_after_warm"]["polish_text_fragment"]["hits"] > 0
    # Deliberately broad: this catches catastrophic cache regressions without
    # making shared CI hardware responsible for millisecond-level variance.
    assert result["warm_total_median_seconds"] <= result["cold_total_seconds"] * 1.75


def test_outer_polish_client_cache_is_not_added_without_measured_value() -> None:
    # _polish_text_fragment owns the expensive pass. Caching this public wrapper
    # as well duplicates nearly the same keys and retained values.
    assert not hasattr(polish_client_text, "cache_info")
