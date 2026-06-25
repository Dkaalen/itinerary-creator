from __future__ import annotations

from pathlib import Path

from scripts.architecture_guards import (
    duplicate_test_path_hits,
    forbidden_normal_ui_hits,
    import_from_hits,
    oversized_core_named_python_files,
    oversized_core_python_files,
    oversized_editor_css_files,
    oversized_frontend_js_files,
    oversized_python_functions,
    oversized_workflow_python_files,
    patch_history_name_hits,
    root_patch_artifact_hits,
    source_contains,
)


ROOT = Path(__file__).resolve().parents[1]


def test_normal_workflow_sources_do_not_contain_visible_bloat_strings() -> None:
    assert forbidden_normal_ui_hits() == ()


def test_file_size_guards_protect_recently_split_frontend_and_workflow_files() -> None:
    assert oversized_frontend_js_files() == ()
    assert oversized_workflow_python_files() == ()
    assert oversized_core_python_files() == ()
    assert oversized_editor_css_files() == ()
    assert oversized_core_named_python_files() == ()


def test_function_size_guard_blocks_new_giant_functions_outside_allowlist() -> None:
    assert oversized_python_functions() == ()


def test_patch_history_and_vague_names_do_not_return_to_high_value_source_dirs() -> None:
    assert patch_history_name_hits() == ()


def test_debug_review_imports_are_lazy_behind_debug_boundaries() -> None:
    assert import_from_hits("app_modules/main_view.py", ("ui.diagnostics_panel", "ui.input_review_panel")) == ()
    assert import_from_hits("app_modules/input_step.py", ("ui.input_review_panel",)) == ()
    assert import_from_hits("app_modules/debug_tools.py", ("ui.diagnostics_panel",)) == ()

    assert source_contains("app_modules/debug_tools.py", "if not is_debug_mode(st.session_state):")
    assert source_contains("app_modules/debug_tools.py", "from ui.diagnostics_panel import")
    assert source_contains("app_modules/input_step.py", "if not is_debug_mode(st.session_state):")
    assert source_contains("app_modules/input_step.py", "from ui.input_review_panel import")


def test_pdf_internal_review_appendix_is_lazy_loaded_only_when_enabled() -> None:
    typed_exporter = (ROOT / "pdf_exporter_modules" / "typed_exporter.py").read_text(encoding="utf-8")

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


def test_patch_artifacts_and_duplicate_tests_do_not_return() -> None:
    assert root_patch_artifact_hits() == ()
    assert duplicate_test_path_hits() == ()
