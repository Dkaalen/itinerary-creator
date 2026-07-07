from __future__ import annotations

import ast
from pathlib import Path
from tests.support.static_contracts import read_contract_text

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "parser_modules"


def _function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_details_facade_delegates_to_responsibility_modules() -> None:
    facade = PARSER / "details.py"
    assert len(facade.read_text(encoding="utf-8").splitlines()) <= 35

    expected_modules = {
        "row_text_standardization.py",
        "detail_extractors.py",
        "title_cleanup.py",
        "title_prose_boundaries.py",
        "list_parsing.py",
        "effective_type_detection.py",
    }
    for module_name in expected_modules:
        assert (PARSER / module_name).exists()

    assert _function_names(facade) == set()


def test_details_responsibilities_are_not_mixed_back_into_facade() -> None:
    facade_text = read_contract_text(PARSER / "details.py")
    forbidden_snippets = [
        "def clean_title(",
        "def split_comma_list(",
        "def detect_effective_type(",
        "def standardize_row_text(",
        "DETAIL_LABELS",
        "DETAIL_MARKERS",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in facade_text


def test_parser_main_is_orchestration_only() -> None:
    parser_main = PARSER / "parser_main.py"
    source = parser_main.read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 230

    for module_name in [
        "date_fields.py",
        "raw_row_context.py",
        "city_inference.py",
        "row_builder.py",
        "row_enrichment.py",
    ]:
        assert (PARSER / module_name).exists()

    forbidden_helpers = [
        "def _parse_itinerary_date(",
        "def _date_derived_hotel_nights(",
        "def _fixed_format_city_only_description(",
        "def _infer_city_from_text(",
    ]
    for helper in forbidden_helpers:
        assert helper not in source


def test_parse_itinerary_still_delegates_to_row_builder_and_enrichment() -> None:
    source = read_contract_text(PARSER / "parser_main.py")
    assert "build_base_row(" in source
    assert "enrich_parsed_row(" in source
