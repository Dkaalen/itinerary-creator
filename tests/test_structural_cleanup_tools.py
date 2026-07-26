from pathlib import Path

from shared import source_text_cleanup as parser_cleanup
from scripts.export_destination_registry import build_registry_export, validate_registry_export
from scripts.module_ownership_audit import run_audit
from scripts.test_group_hygiene import build_report
from shared import text_cleanup_rules
from text_polish_modules import text_cleanup as polish_cleanup
from itinerary_generation.transport_domain.routes import get_transport_route_facts


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
    facts = get_transport_route_facts(
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
    from itinerary_domain.row_type_detection import detect_effective_type

    assert detect_effective_type("Activity", "Arctic Route Coach Transfer", "") == "Transport"
    assert detect_effective_type("Activity", "Tallinn day excursion", "Guided tour of the old town with ferry logistics") == "Activity"
    assert detect_effective_type("Transfer", "Overnight train", "Private sleeper compartment on the night train") == "Train"


def test_route_point_parser_split_keeps_known_route_patterns() -> None:
    from itinerary_domain.source_route_parsing import extract_route_points

    assert extract_route_points("Train: Oslo to Bergen") == ("Oslo", "Bergen")
    assert extract_route_points("Day train, Rovaniemi - Helsinki") == ("Rovaniemi", "Helsinki")
    assert extract_route_points("Flight Bergen o Svolvær self-arranged") == ("Bergen", "Svolvær")


def test_test_group_hygiene_moves_core_quality_modules_out_of_full_only() -> None:
    report = build_report()
    full_only = set(report["full_only_test_modules"])

    assert "tests/test_transport_domain_regression.py" not in full_only
    assert "tests/test_code_cleanup_hygiene_regression.py" not in full_only
    assert report["full_only_test_module_count"] <= 75

def test_activity_description_helpers_delegate_keyword_rules() -> None:
    from itinerary_generation.activity_description_helpers import get_activity_description

    assert get_activity_description({"title": "Whale watching", "city": "Tromsø"}).startswith("Join a whale watching")
    assert "Tromsø" in get_activity_description({"title": "Whale watching", "city": "Tromsø"})


def test_day_planner_keeps_split_decision_helpers_behavior() -> None:
    from itinerary_generation.day_planner import plan_day

    plan = plan_day([{"type": "Activity", "title": "Guided walking tour", "city": "Oslo"}])
    assert plan.pattern == "single_activity_day"
    assert plan.skip_empty_activity_rows is True


def test_test_group_hygiene_covers_all_current_modules_without_duplicates() -> None:
    report = build_report()
    assert report["full_only_test_module_count"] == 0
    assert report["duplicate_group_entry_count"] == 0


def test_module_ownership_audit_reports_facade_importer_counts(tmp_path: Path) -> None:
    (tmp_path / "facade.py").write_text("from target import *  # noqa: F401,F403\n__all__ = []\n", encoding="utf-8")
    (tmp_path / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "consumer.py").write_text("from facade import VALUE\n", encoding="utf-8")

    audit = run_audit(tmp_path, file_line_limit=999, function_line_limit=999)

    assert audit.facade_importers["facade.py"] == ("consumer.py",)


def test_test_group_catalog_split_preserves_public_group_api() -> None:
    from scripts import test_groups
    from scripts.test_group_catalog import GROUPS, QUALITY_TESTS

    assert test_groups.GROUPS is GROUPS
    assert "tests/test_structured_core_model_validation.py" in GROUPS["architecture"]
    assert "tests/test_image_matcher_selection_fallbacks.py" in GROUPS["images"]
    assert QUALITY_TESTS


def test_architecture_guard_config_split_preserves_runner() -> None:
    from scripts.architecture_guards import run_architecture_checks
    from scripts.architecture_guard_config import TOP_LEVEL_COMPATIBILITY_FACADES

    assert "itinerary_parser.py" in TOP_LEVEL_COMPATIBILITY_FACADES
    assert run_architecture_checks() == ()


def test_deletion_candidate_audit_is_handover_only() -> None:
    from scripts.deletion_candidate_audit import build_report

    report = build_report()

    assert report.candidates == ()
    assert any(item.safety_note.startswith("documented public") for item in report.held_back)


def test_facade_audit_resolves_relative_and_package_submodule_imports(tmp_path: Path) -> None:
    from scripts.audit_legacy_facades import audit_modules

    package = tmp_path / "images"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "relative_consumer.py").write_text("from . import target\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("from images import target\n", encoding="utf-8")

    audit = {item.module: item for item in audit_modules(tmp_path)}

    assert audit["images.target"].production_importers == ("app", "images.relative_consumer")
    assert audit["images"].path == "images/__init__.py"


def test_deletion_candidate_audit_protects_entrypoint_and_finds_dead_facade(tmp_path: Path) -> None:
    from scripts.deletion_candidate_audit import build_report

    package = tmp_path / "ui"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "owner.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "dead_facade.py").write_text(
        '"""Compatibility facade."""\nfrom ui.owner import VALUE\n__all__ = ["VALUE"]\n',
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    report = build_report(tmp_path)

    assert [item.path for item in report.candidates] == ["ui/dead_facade.py"]
    app_finding = next(item for item in report.held_back if item.path == "app.py")
    assert app_finding.safety_note == "production application entrypoint"


def test_parser_generation_ownership_audit_reports_review_signals(tmp_path: Path) -> None:
    from scripts.parser_generation_ownership_audit import build_report

    source = tmp_path / "itinerary_generation" / "day_render_example.py"
    source.parent.mkdir(parents=True)
    source.write_text("def render(row):\n    if row.get('effective_type') == 'Train':\n        return row.get('route_origin')\n", encoding="utf-8")

    report = build_report(tmp_path)

    assert report.scanned_files == 1
    assert report.signal_count >= 1
    assert "classification_inside_writer_layer" in report.signals_by_rule


def test_transport_domain_route_summary_owns_title_route_facts() -> None:
    from itinerary_generation.transport_domain.route_summary import (
        infer_route_endpoints_from_title,
        infer_travel_mode_from_title,
    )

    assert infer_route_endpoints_from_title("Travel from Oslo to Bergen") == ("Oslo", "Bergen")
    assert infer_route_endpoints_from_title("Norway in a Nutshell to Flåm") == ("", "Flåm")
    assert infer_travel_mode_from_title("Coastal cruise transfer to Bergen") == "coastal_cruise"


def test_parser_generation_audit_allows_transport_domain_imports(tmp_path: Path) -> None:
    from scripts.parser_generation_ownership_audit import build_report

    source = tmp_path / "normalizer_modules" / "transport_example.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "from itinerary_generation.transport_domain.routes import get_route_points_for_transport\n",
        encoding="utf-8",
    )

    report = build_report(tmp_path)

    assert report.signal_count == 0


def test_static_data_hygiene_report_validates_registry() -> None:
    from scripts.static_data_hygiene import build_report

    report = build_report()

    assert report.destination_count > 100
    assert report.alias_record_count > 100
    assert report.registry_validation_errors == ()


def test_test_suite_audit_writes_handover_reports(tmp_path: Path) -> None:
    from scripts.test_suite_audit import build_report, build_report_summary, write_report

    text = build_report()
    assert build_report_summary(text)["Discovered test modules"] >= 1
    md_path, json_path = write_report(text, md_path=tmp_path / "latest.md", json_path=tmp_path / "latest.json")

    assert md_path.exists()
    assert json_path.exists()


def test_parser_generation_audit_keeps_route_owner_allowlist_specific(tmp_path: Path) -> None:
    from scripts.parser_generation_ownership_audit import build_report

    owner = tmp_path / "itinerary_generation" / "route_intelligence.py"
    consumer = tmp_path / "itinerary_generation" / "day_title_planner.py"
    owner.parent.mkdir(parents=True)
    owner.write_text(
        "from itinerary_generation.transport_domain.routes import get_route_points_for_transport\n"
        "def owned(row):\n    return get_route_points_for_transport(row)\n",
        encoding="utf-8",
    )
    consumer.write_text(
        "from itinerary_generation.transport_domain.routes import get_route_points_for_transport\n"
        "def consumer(row):\n    return get_route_points_for_transport(row)\n",
        encoding="utf-8",
    )

    report = build_report(tmp_path)

    assert report.signal_count == 2
    assert {signal.path for signal in report.signals} == {"itinerary_generation/day_title_planner.py"}


def test_shared_client_text_repair_is_used_by_transport_safety() -> None:
    from itinerary_generation.transport_safety import repair_messy_client_text as transport_repair
    from shared.client_text_repair import repair_messy_client_text

    assert transport_repair is repair_messy_client_text
    assert repair_messy_client_text("Private bustation tranfer from Tromso") == "Private Bus Station transfers from Tromsø"
    assert repair_messy_client_text("Self tranfser to Kussamo Bus Stop") == "Self transfer to Kuusamo Bus Stop"
    assert repair_messy_client_text("Coach Transfer to Santa Cluas Village") == "Coach Transfer to Santa Claus Village"
