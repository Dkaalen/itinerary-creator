"""Fixture selection and review building for real-output QA."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, build_candidate_index, select_random_candidates
from scripts.real_output_qa.models import CandidateOutputReview
from scripts.real_output_qa.rendering import render_candidate_review


def select_candidates(
    *,
    manifest_path: Path,
    sample_size: int,
    seed: int,
    include_all: bool = False,
    include_workbooks: Iterable[str] = (),
    fixture_ids: Iterable[str] = (),
):
    """Select fixture-bank candidates for review."""

    candidates = build_candidate_index(manifest_path)
    workbook_terms = tuple(term.casefold() for term in include_workbooks if term)
    fixture_terms = tuple(term.casefold() for term in fixture_ids if term)
    if workbook_terms:
        candidates = tuple(candidate for candidate in candidates if any(term in candidate.workbook_path.name.casefold() for term in workbook_terms))
    if fixture_terms:
        candidates = tuple(
            candidate
            for candidate in candidates
            if any(term == candidate.fixture_id.casefold() or term in candidate.fixture_id.casefold() for term in fixture_terms)
        )
    if fixture_terms or include_all:
        return candidates
    return select_random_candidates(candidates, sample_size=sample_size, seed=seed)


def build_reviews(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    sample_size: int = 5,
    seed: int = 0,
    include_all: bool = False,
    include_workbooks: Iterable[str] = (),
    fixture_ids: Iterable[str] = (),
) -> tuple[CandidateOutputReview, ...]:
    """Render selected fixture candidates into review snapshots."""

    selected = select_candidates(
        manifest_path=manifest_path,
        sample_size=sample_size,
        seed=seed,
        include_all=include_all,
        include_workbooks=include_workbooks,
        fixture_ids=fixture_ids,
    )
    return tuple(render_candidate_review(candidate) for candidate in selected)


__all__ = ["build_reviews", "select_candidates"]
