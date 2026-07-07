from __future__ import annotations

from pathlib import Path

from parser_modules.place_parsing import is_valid_city_value
from scripts.random_quality_check_itineraries import build_random_quality_report
from scripts.real_excel_fixture_bank import (
    DEFAULT_MANIFEST,
    build_candidate_index,
    load_manifest,
    select_random_candidates,
)

ROOT = Path(__file__).resolve().parents[1]


def test_real_excel_manifest_lists_uploaded_workbooks() -> None:
    specs = load_manifest(DEFAULT_MANIFEST)

    assert len(specs) == 10
    assert {spec.path.name for spec in specs} == {
        "Standard-Itinerary-Denmark.xlsx",
        "Standard-Itinerary-Finland.xlsx",
        "Standard-Itinerary-Iceland.xlsx",
        "Standard-Itinerary-Finland-Norway.xlsx",
        "Standard-Itinerary-Norway.xlsx",
        "Standard-Itinerary-Sweden.xlsx",
        "Calculation-template-Nordics.xlsx",
        "Calculation-template-DK0807.xlsx",
        "Calculation-template-DK0801.xlsx",
        "Calculation-template-202614.xlsx",
    }
    assert all(spec.path.exists() for spec in specs)


def test_real_excel_fixture_bank_extracts_many_candidate_sheets() -> None:
    candidates = build_candidate_index(DEFAULT_MANIFEST)
    workbook_names = {candidate.workbook_path.name for candidate in candidates}

    assert len(candidates) >= 70
    assert len(workbook_names) == 10
    assert all(candidate.raw_text.startswith("\t\tDay") or "Day 1" in candidate.raw_text for candidate in candidates)
    assert all(candidate.row_count >= 3 for candidate in candidates)
    assert all(candidate.day_count >= 1 for candidate in candidates)


def test_random_candidate_selection_is_seeded_and_spread_across_workbooks() -> None:
    candidates = build_candidate_index(DEFAULT_MANIFEST)

    first = select_random_candidates(candidates, sample_size=6, seed=6200)
    second = select_random_candidates(candidates, sample_size=6, seed=6200)

    assert [candidate.fixture_id for candidate in first] == [candidate.fixture_id for candidate in second]
    assert len({candidate.workbook_path.name for candidate in first}) >= 3


def test_seeded_random_quality_check_passes_product_output_guards() -> None:
    report = build_random_quality_report(sample_size=4, seed=6200)

    assert report["sample_size"] == 4
    assert report["error_count"] == 0
    assert report["bank_summary"]["workbook_count"] == 10


def test_currency_codes_are_not_accepted_as_context_cities() -> None:
    assert not is_valid_city_value("EUR")
    assert not is_valid_city_value("NOK")

