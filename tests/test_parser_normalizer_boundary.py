from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

import itinerary_parser
import normalizer
from itinerary_generation.reference_corpus import iceland_reference_payload
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows, normalize_row

ROOT = Path(__file__).resolve().parents[1]
REAL_INPUTS = ROOT / "tests" / "fixtures" / "real_inputs"
PARSER_ROOT = ROOT / "parser_modules"


def _line(day: str, row_type: str, city: str, details: str, *, start: str = "01/01/2027", end: str = "") -> str:
    return "\t".join(["", day, row_type, "", start, end, "", "", "", city, details])


def _normalized(raw: str) -> list[dict]:
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_public_parser_and_normalizer_apis_are_explicit() -> None:
    assert itinerary_parser.__all__ == (
        "clean_room_category",
        "clean_space",
        "extract_duration_from_description",
        "extract_includes_from_description",
        "extract_luggage_included",
        "extract_meeting_point_from_description",
        "extract_time_from_description",
        "normalize_time_text",
        "parse_hotel_details",
        "parse_itinerary",
        "parse_meal_plan",
    )
    assert normalizer.__all__ == (
        "normalize_row",
        "normalize_itinerary_rows",
        "warn_suspicious_city",
    )


def test_raw_parser_does_not_assign_semantic_type_or_route_facts() -> None:
    raw = _line(
        "Day 1",
        "Transfer",
        "Oslo",
        "Flight: 14:20 Copenhagen Airport Direct 15:30 Oslo Airport",
    )

    parsed = parse_itinerary(raw)[0]
    normalized = normalize_itinerary_rows([parsed])[0]

    assert parsed["type"] == "Transfer"
    assert parsed["effective_type"] == "Transfer"
    assert "route_origin" not in parsed
    assert "route_destination" not in parsed
    assert normalized["type"] == "Transfer"
    assert normalized["effective_type"] == "Flight"
    assert normalized["route_origin"] == "Copenhagen Airport"
    assert normalized["route_destination"] == "Oslo Airport"


def test_contextual_city_propagation_is_normalizer_owned() -> None:
    raw = "\n".join(
        [
            _line(
                "Day 1",
                "Hotel",
                "Oslo",
                "Example Hotel - Standard Double Room - Breakfast included",
                end="02/01/2027",
            ),
            _line("Day 1", "Activity", "", "Museum visit"),
        ]
    )

    parsed = parse_itinerary(raw)
    assert parsed[1]["city"] == ""

    normalized = normalize_itinerary_rows(parsed)
    assert normalized[1]["city"] == "Oslo"


def test_source_owned_activity_classification_runs_after_parsing() -> None:
    raw = _line(
        "Day 2",
        "Activity",
        "Helsinki",
        "Excursion to Tallinn by ferry with a self-guided Old Town visit and return sailing",
    )

    parsed = parse_itinerary(raw)[0]
    normalized = normalize_itinerary_rows([parsed])[0]

    assert parsed["type"] == parsed["effective_type"] == "Activity"
    assert normalized["effective_type"] == "Activity"
    assert normalized["activity_product"]["product_type"] == "ferry_excursion"


def test_normalize_row_is_non_mutating_and_retains_unknown_fields() -> None:
    source = {
        "day": "Day 1",
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Oslo",
        "title": "Guided city walk",
        "details": "Guided city walk",
        "supplier_extension": {"contract": "retain", "codes": ["A", "B"]},
    }
    before = copy.deepcopy(source)

    result = normalize_row(source)

    assert source == before
    assert result["supplier_extension"] == before["supplier_extension"]
    assert result["supplier_extension"] is not source["supplier_extension"]


def test_normalization_preserves_end_to_end_source_identity() -> None:
    source = {
        "row_id": "Hotels:27",
        "source_sheet": "Hotels",
        "source_row": 27,
        "local_library_identity": "Hotels:27:abc123",
        "source_url": "https://supplier.example/internal-product",
        "source_urls": ["https://supplier.example/internal-product"],
        "day": "Day 1",
        "type": "Hotel",
        "effective_type": "Hotel",
        "city": "Oslo",
        "title": "Example Hotel",
        "original_title": "Example Hotel",
        "details": "Example Hotel - Standard Double Room - Breakfast included",
        "hotel_name": "Example Hotel",
        "hotel_nights": "1",
    }

    result = normalize_itinerary_rows([source])[0]

    for key in ("row_id", "source_sheet", "source_row", "local_library_identity", "source_url", "source_urls"):
        assert result[key] == source[key]


def test_identical_workbook_products_remain_distinct_by_source_identity() -> None:
    base = {
        "day": "Day 1",
        "type": "Activity",
        "effective_type": "Activity",
        "city": "Oslo",
        "title": "Oslo Walking Tour",
        "original_title": "Oslo Walking Tour",
        "details": "Oslo Walking Tour",
    }
    rows = [
        {**base, "row_id": "Activities:11", "source_sheet": "Activities", "source_row": 11},
        {**base, "row_id": "Activities:12", "source_sheet": "Activities", "source_row": 12},
        {**base, "row_id": "Transfers:11", "source_sheet": "Transfers", "source_row": 11},
    ]

    normalized = normalize_itinerary_rows(rows)

    assert len(normalized) == 3
    assert [(row["source_sheet"], row["source_row"], row["row_id"]) for row in normalized] == [
        ("Activities", 11, "Activities:11"),
        ("Activities", 12, "Activities:12"),
        ("Transfers", 11, "Transfers:11"),
    ]


@pytest.mark.parametrize(
    ("raw", "expected_type"),
    [
        (_line("Day 1", "Hotel", "Oslo", "Example Hotel - Standard Double Room - Breakfast included", end="02/01/2027"), "Hotel"),
        (_line("Day 1", "Transfer", "Oslo", "Private transfer from Oslo Airport to your hotel"), "Transfer"),
        (_line("Day 1", "Transport", "Oslo", "Coach from Oslo to Lillehammer"), "Transport"),
        (_line("Day 1", "Activity", "Oslo", "Guided Oslo Walking Tour"), "Activity"),
        (_line("Day 1", "Leisure", "Oslo", "Day at leisure"), "Leisure"),
        (_line("Day 1", "Flight", "Oslo", "Flight from Bergen to Oslo"), "Flight"),
        (_line("Day 1", "Cruise", "Bergen", "Overnight cruise from Bergen to Ålesund"), "Cruise"),
    ],
)
def test_supported_row_types_cross_the_public_pipeline(raw: str, expected_type: str) -> None:
    rows = _normalized(raw)
    assert len(rows) == 1
    assert rows[0]["effective_type"] == expected_type


def test_optional_self_arranged_missing_date_and_multiline_rows_survive_pipeline() -> None:
    raw = "\n".join(
        [
            _line("Day 1", "Optional", "Oslo", "Optional guided museum visit", start=""),
            _line("Day 2", "Transfer", "Oslo", "Flight self-arranged, cost not included", start=""),
            _line("Day 3", "Activity", "Bergen", "Bergen Food Tour\nIncludes local tastings and a guide", start=""),
        ]
    )

    rows = _normalized(raw)

    assert len(rows) == 3
    assert rows[0]["is_optional"] is True
    assert rows[0]["commercial_status"] == "optional"
    assert rows[1]["effective_type"] == "Flight"
    assert rows[1]["commercial_status"] == "self_arranged"
    assert rows[1]["start_date"] == ""
    assert rows[2]["title"] == "Bergen Food Tour"
    assert "local tastings" in rows[2]["details"]


def test_malformed_and_unknown_source_rows_have_explicit_behavior() -> None:
    assert parse_itinerary("not a tabular itinerary row") == []

    unknown = _normalized(_line("Day 1", "Custom Supplier Item", "Oslo", "Supplier-defined service"))[0]
    assert unknown["type"] == "Custom Supplier Item"
    assert unknown["effective_type"] == "Custom Supplier Item"
    assert unknown["details"] == "Supplier-defined service"


def test_norway_in_a_nutshell_is_enriched_downstream() -> None:
    raw = _line(
        "Day 2",
        "Activity",
        "Voss",
        "Oslo to Flåm: Norway in a Nutshell Part 1 | Train 08:23 Oslo - 13:04 Myrdal | Bus 17:25 Gudvangen - 18:25 Voss",
    )

    parsed = parse_itinerary(raw)[0]
    normalized = normalize_itinerary_rows([parsed])[0]

    assert parsed["effective_type"] == "Activity"
    assert "route_origin" not in parsed
    assert normalized["effective_type"] == "Transport"
    assert normalized["route_origin"] == "Oslo"
    assert normalized["route_destination"] == "Voss"
    assert normalized["activity_product"]["canonical_family"] == "norway_in_a_nutshell"


def test_group_tour_master_rows_keep_source_identity_and_receive_domain_contract() -> None:
    sheet = next(item for item in iceland_reference_payload()["sheets"] if item["sheet_name"] == "5D GTW")
    source_rows = copy.deepcopy(sheet["rows"])

    normalized = normalize_itinerary_rows(
        source_rows,
        source_name=sheet["sheet_name"],
        group_tour_season=sheet["season"],
    )
    master = next(row for row in normalized if row.get("group_tour_role") == "package_master")

    assert master["row_id"]
    assert master["group_tour_package_context"]["season"] == "winter"
    assert master["group_tour_package_context"]["duration_days"] == 3


def test_source_owned_group_tour_commercial_types_are_not_reclassified() -> None:
    sheet = next(item for item in iceland_reference_payload()["sheets"] if item["sheet_name"] == "10D GTS")

    normalized = normalize_itinerary_rows(
        copy.deepcopy(sheet["rows"]),
        source_name=sheet["sheet_name"],
        group_tour_season=sheet["season"],
    )
    transfer_packages = [
        row for row in normalized if row.get("group_tour_commercial_category") == "transfer_package"
    ]

    assert len(transfer_packages) == 4
    assert all(row["type"] == "Transfer package" for row in transfer_packages)
    assert all(row["group_tour_role"] == "commercial_item" for row in transfer_packages)



def test_real_fixture_normalization_is_idempotent() -> None:
    checked_rows = 0
    for path in sorted(REAL_INPUTS.glob("*.txt")):
        first = _normalized(path.read_text(encoding="utf-8"))
        second = normalize_itinerary_rows(first)
        checked_rows += len(first)
        assert second == first, path.name

    assert checked_rows == 484


def test_parser_package_has_no_semantic_classification_or_normalizer_dependency() -> None:
    forbidden_import_prefixes = (
        "itinerary_domain.row_type",
        "itinerary_generation.transport_domain",
        "normalizer",
        "normalizer_modules",
    )
    offenders: list[str] = []
    for path in sorted((ROOT / "parser_modules").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                if name.startswith(forbidden_import_prefixes):
                    offenders.append(f"{path.name}: {name}")
    assert offenders == []


def test_production_consumers_do_not_import_parser_internals() -> None:
    offenders: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".git", "__pycache__", ".pytest_cache", "tests"} for part in path.parts):
            continue
        if path == ROOT / "itinerary_parser.py" or PARSER_ROOT in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                if name == "parser_modules" or name.startswith("parser_modules."):
                    offenders.append(f"{path.relative_to(ROOT)}: {name}")
    assert offenders == []


def test_retired_parser_semantic_modules_are_absent() -> None:
    retired = {
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
    }
    assert [name for name in sorted(retired) if (ROOT / "parser_modules" / name).exists()] == []
