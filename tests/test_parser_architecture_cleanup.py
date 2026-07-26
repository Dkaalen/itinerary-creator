from __future__ import annotations

import ast
from pathlib import Path
from tests.support.static_contracts import read_contract_text

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "parser_modules"


def _function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_details_namespace_delegates_to_parser_extraction_modules() -> None:
    facade = PARSER / "details.py"
    assert len(facade.read_text(encoding="utf-8").splitlines()) <= 35

    expected_modules = {
        "detail_extractors.py",
        "title_cleanup.py",
        "title_prose_boundaries.py",
        "list_parsing.py",
    }
    for module_name in expected_modules:
        assert (PARSER / module_name).exists()

    assert _function_names(facade) == set()


def test_details_responsibilities_are_not_mixed_back_into_namespace() -> None:
    facade_text = read_contract_text(PARSER / "details.py")
    forbidden_snippets = [
        "def clean_title(",
        "def split_comma_list(",
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


def test_semantic_type_and_source_standardization_have_downstream_owners() -> None:
    domain = ROOT / "itinerary_domain"
    normalizer = ROOT / "normalizer_modules"

    for path in (
        domain / "input_row_quality.py",
        domain / "row_type_detection.py",
        domain / "row_type_priority.py",
        domain / "row_type_rules.py",
        domain / "source_place_values.py",
        domain / "source_route_parsing.py",
        ROOT / "shared" / "row_type_values.py",
        ROOT / "shared" / "source_text_cleanup.py",
        ROOT / "shared" / "source_time.py",
        normalizer / "domain_enrichment.py",
        normalizer / "source_row_standardization.py",
    ):
        assert path.exists()

    parser_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(PARSER.glob("*.py"))
    )
    assert "detect_effective_type(" not in parser_text
    assert "apply_effective_type_and_routes" not in parser_text


def test_retired_semantic_parser_owners_are_deleted() -> None:
    for module_name in (
        "contextual_city.py",
        "effective_type_detection.py",
        "effective_type_priority.py",
        "effective_type_rules.py",
        "place_parsing.py",
        "place_values.py",
        "route_parsing.py",
        "row_quality.py",
        "row_text_standardization.py",
        "text_cleanup.py",
        "time_duration.py",
        "time_finders.py",
        "time_normalize.py",
        "time_parsing.py",
        "time_tokens.py",
        "transport_titles.py",
    ):
        assert not (PARSER / module_name).exists()


def test_parser_state_tracks_only_raw_row_orchestration_state() -> None:
    source = read_contract_text(PARSER / "parser_state.py")
    assert "last_context_city" not in source
    assert "pending_city_rows" not in source
    assert "extract_route_points" not in source
    assert "apply_context" not in source
