from pathlib import Path

from parser_modules import text_cleanup as parser_cleanup
from scripts.export_destination_registry import build_registry_export, validate_registry_export
from scripts.module_ownership_audit import run_audit
from scripts.test_group_hygiene import build_report
from shared import text_cleanup_rules
from text_polish_modules import text_cleanup as polish_cleanup
from itinerary_generation.transport_domain.facts import build_transport_facts


def test_text_cleanup_rules_are_shared_across_parser_and_polish() -> None:
    assert parser_cleanup.COMMON_TEXT_REPLACEMENTS is text_cleanup_rules.COMMON_TEXT_REPLACEMENTS
    assert parser_cleanup.COMPILED_COMMON_TEXT_REPLACEMENTS is text_cleanup_rules.COMPILED_COMMON_TEXT_REPLACEMENTS
    assert polish_cleanup.CASE_REPLACEMENTS is text_cleanup_rules.CASE_REPLACEMENTS
    assert polish_cleanup.PROPER_NOUN_REPLACEMENTS is text_cleanup_rules.PROPER_NOUN_REPLACEMENTS
    assert parser_cleanup.fix_common_text("Actvity in Hlesinki with Free wifi") == "Activity in Helsinki with Free Wi-Fi"


def test_real_output_ownership_audit_runs_on_tiny_repo(tmp_path: Path) -> None:
    sample = tmp_path / "sample_cleanup.py"
    sample.write_text(
        "import re\n\n"
        "def large():\n"
        + "\n".join("    re.sub(r'a', 'b', 'a')" for _ in range(12))
        + "\n",
        encoding="utf-8",
    )
    audit = run_audit(tmp_path, file_line_limit=5, function_line_limit=10)
    assert audit.overworked_files
    assert audit.long_functions
    assert audit.duplicate_rule_hotspots


def test_test_group_hygiene_report_has_expected_shape() -> None:
    report = build_report()
    assert report["all_test_module_count"] >= report["grouped_test_module_count"]
    assert isinstance(report["full_only_test_modules"], list)
    assert isinstance(report["stale_group_entries"], list)


def test_destination_registry_export_is_valid() -> None:
    data = build_registry_export()
    assert data["destination_count"] > 100
    assert validate_registry_export(data) == []


def test_transport_facts_extracts_route_without_copy_decisions() -> None:
    facts = build_transport_facts(
        {
            "effective_type": "Train",
            "title": "Train: Oslo to Bergen",
            "details": "Direct train Oslo to Bergen",
            "city": "Oslo",
        }
    )
    assert facts.mode == "train"
    assert facts.origin == "Oslo"
    assert facts.destination == "Bergen"
    assert facts.display_route == "Oslo to Bergen"


def test_day_facts_builder_uses_split_row_signal_scanner() -> None:
    from itinerary_generation.day_fact_signals import scan_day_row_signals
    from itinerary_generation.day_facts import build_day_facts

    rows = [
        {"type": "Train", "effective_type": "Train", "title": "Train: Oslo to Bergen", "city": "Oslo"},
        {"type": "Hotel", "effective_type": "Hotel", "title": "Hotel in Bergen", "city": "Bergen"},
    ]
    signals = scan_day_row_signals(rows)
    facts = build_day_facts(rows)

    assert signals.route_origins == ["Oslo"]
    assert signals.route_destinations == ["Bergen"]
    assert facts.route_origin == "Oslo"
    assert facts.route_destination == "Bergen"
    assert facts.overnight_city == "Bergen"


def test_effective_type_priority_helpers_preserve_transport_activity_order() -> None:
    from parser_modules.effective_type_detection import detect_effective_type

    assert detect_effective_type("Activity", "Arctic Route Coach Transfer", "") == "Transport"
    assert detect_effective_type("Activity", "Tallinn day excursion", "Guided tour of the old town with ferry logistics") == "Activity"
    assert detect_effective_type("Transfer", "Overnight train", "Private sleeper compartment on the night train") == "Train"


def test_route_point_parser_split_keeps_known_route_patterns() -> None:
    from parser_modules.place_parsing import extract_route_points

    assert extract_route_points("Train: Oslo to Bergen") == ("Oslo", "Bergen")
    assert extract_route_points("Day train, Rovaniemi - Helsinki") == ("Rovaniemi", "Helsinki")
    assert extract_route_points("Flight Bergen o Svolvær self-arranged") == ("Bergen", "Svolvær")


def test_test_group_hygiene_moves_core_quality_modules_out_of_full_only() -> None:
    report = build_report()
    full_only = set(report["full_only_test_modules"])

    assert "tests/test_transport_domain_regression.py" not in full_only
    assert "tests/test_code_cleanup_hygiene_regression.py" not in full_only
    assert report["full_only_test_module_count"] <= 75
