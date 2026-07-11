from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text

from scripts import architecture_guards
from scripts.architecture_guards import (
    destination_transport_cycle_hits,
    itinerary_domain_generation_import_hits,
    duplicate_shared_clean_space_hits,
    duplicate_test_path_hits,
    forbidden_normal_ui_hits,
    generation_implementation_core_import_hits,
    import_from_hits,
    oversized_cleaned_generation_core_facades,
    oversized_core_named_python_files,
    oversized_core_python_files,
    oversized_editor_css_files,
    oversized_frontend_js_files,
    oversized_python_functions,
    oversized_streamlit_style_files,
    oversized_workflow_python_files,
    patch_history_name_hits,
    root_patch_artifact_hits,
    source_contains,
    top_level_compatibility_facade_hits,
)


ROOT = Path(__file__).resolve().parents[1]


def test_normal_workflow_sources_do_not_contain_visible_bloat_strings() -> None:
    assert forbidden_normal_ui_hits() == ()


def test_file_size_guards_protect_recently_split_frontend_and_workflow_files() -> None:
    assert oversized_frontend_js_files() == ()
    assert oversized_workflow_python_files() == ()
    assert oversized_core_python_files() == ()
    assert oversized_editor_css_files() == ()
    assert oversized_streamlit_style_files() == ()
    assert oversized_core_named_python_files() == ()
    assert oversized_cleaned_generation_core_facades() == ()


def test_function_size_guard_blocks_new_giant_functions_outside_allowlist() -> None:
    assert oversized_python_functions() == ()


def test_and_vague_names_do_not_return_to_high_value_source_dirs() -> None:
    assert patch_history_name_hits() == ()


def test_debug_review_imports_are_lazy_behind_debug_boundaries() -> None:
    assert import_from_hits("app_modules/main_view.py", ("ui.diagnostics_panel", "ui.input_review_panel")) == ()
    assert import_from_hits("app_modules/generation_messages.py", ("ui.input_review_panel",)) == ()
    assert import_from_hits("app_modules/debug_tools.py", ("ui.diagnostics_panel",)) == ()

    assert source_contains("app_modules/debug_tools.py", "if not is_debug_mode(st.session_state):")
    assert source_contains("app_modules/debug_tools.py", "from ui.diagnostics_panel import")
    assert source_contains("app_modules/generation_messages.py", "if not is_debug_mode(state):")
    assert source_contains("app_modules/generation_messages.py", "from ui.input_review_panel import")


def test_pdf_internal_review_appendix_is_lazy_loaded_only_when_enabled() -> None:
    typed_exporter = read_contract_text(ROOT / "pdf_exporter_modules" / "typed_exporter.py")

    assert import_from_hits("pdf_exporter_modules/typed_exporter.py", ("pdf_exporter_modules.pdf_internal_review_appendix",)) == ()
    assert "if profile.include_internal_notes:" in typed_exporter
    assert typed_exporter.index("if profile.include_internal_notes:") < typed_exporter.index(
        "_render_internal_review_appendix(render_document, story, styles)"
    )


def test_right_inspector_does_not_depend_on_canvas_image_replacement_modules() -> None:
    inspector_sources = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "visual_editor_component/frontend/js").glob("editor_inspector*.js")
    )

    forbidden = (
        "renderImageToolOverlay",
        "data-img-action",
        "data-cover-img-action",
        "inspectorImageUploadInput",
        "replacement image",
        "Why this image",
    )
    for marker in forbidden:
        assert marker not in inspector_sources


def test_and_duplicate_tests_do_not_return() -> None:
    assert root_patch_artifact_hits() == ()
    assert duplicate_test_path_hits() == ()


def test_shared_clean_space_is_the_single_source_of_truth() -> None:
    assert duplicate_shared_clean_space_hits() == ()


def test_top_level_compatibility_facades_stay_thin() -> None:
    assert top_level_compatibility_facade_hits() == ()


def test_destination_transport_import_cycle_does_not_return() -> None:
    assert destination_transport_cycle_hits() == ()


def test_cleaned_generation_facades_do_not_reabsorb_implementation_imports() -> None:
    assert generation_implementation_core_import_hits() == ()


def test_architecture_guard_cli_passes_current_tree(capsys) -> None:
    assert architecture_guards.main(()) == 0

    captured = capsys.readouterr()
    assert "Architecture guards passed." in captured.out
    assert captured.err == ""


def test_architecture_guard_cli_reports_failures(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        architecture_guards,
        "forbidden_normal_ui_hits",
        lambda: (architecture_guards.SourceHit("app_modules/main_view.py", "Advanced tools"),),
    )

    assert architecture_guards.main(()) == 1

    captured = capsys.readouterr()
    assert "Architecture guards failed:" in captured.err
    assert "Advanced tools" in captured.err


def test_neutral_itinerary_domain_does_not_import_generation() -> None:
    assert itinerary_domain_generation_import_hits() == ()


def test_parser_generation_ownership_audit_has_no_signals() -> None:
    from scripts.parser_generation_ownership_audit import build_report

    assert build_report().signal_count == 0


def test_static_data_hygiene_has_no_actionable_signals() -> None:
    from scripts.static_data_hygiene import build_report

    report = build_report()
    assert report.registry_validation_errors == ()
    assert [signal for signal in report.signals if signal.severity != "info"] == []
