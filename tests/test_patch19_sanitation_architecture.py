from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tree(relative_path: str) -> ast.AST:
    return ast.parse((ROOT / relative_path).read_text(encoding="utf-8"), filename=relative_path)


def _imported_modules(relative_path: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(_tree(relative_path)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _call_names(relative_path: str) -> list[str]:
    names: list[str] = []
    for node in ast.walk(_tree(relative_path)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.append(node.func.attr)
    return names


def test_three_sanitation_stages_have_explicit_non_forwarding_owners() -> None:
    owners = (
        "shared/source_text_cleanup.py",
        "itinerary_domain/field_sanitation.py",
        "itinerary_generation/final_document_sanitation.py",
    )
    for relative_path in owners:
        assert (ROOT / relative_path).is_file()
        assert len(_tree(relative_path).body) > 3

    for retired in (
        "itinerary_generation/supplier_cleanup_brain.py",
        "itinerary_generation/client_copy_sanitation.py",
        "itinerary_generation/client_sanitizer.py",
    ):
        assert not (ROOT / retired).exists()


def test_parser_and_source_cleanup_cannot_import_final_document_sanitation() -> None:
    parser_paths = [ROOT / "itinerary_parser.py", *(ROOT / "parser_modules").rglob("*.py")]
    source_paths = [ROOT / "shared/source_text_cleanup.py"]

    for path in (*parser_paths, *source_paths):
        relative = path.relative_to(ROOT).as_posix()
        imports = _imported_modules(relative)
        assert "itinerary_generation.final_document_sanitation" not in imports
        assert "itinerary_domain.field_sanitation" not in imports


def test_supplier_cleanup_does_not_apply_customer_semantic_polish() -> None:
    source = (ROOT / "shared/source_text_cleanup.py").read_text(encoding="utf-8")
    imports = _imported_modules("shared/source_text_cleanup.py")

    assert "text_polish" not in imports
    assert "polish_client_text" not in source
    assert "Northern Lights" not in source
    assert "sanitize_customer_field" not in source


def test_field_sanitation_has_no_parser_normalizer_or_document_traversal_dependency() -> None:
    imports = _imported_modules("itinerary_domain/field_sanitation.py")

    forbidden_prefixes = (
        "itinerary_parser",
        "parser_modules",
        "normalizer",
        "normalizer_modules",
        "itinerary_generation.final_document_sanitation",
        "itinerary_generation.render_document_builder",
        "itinerary_generation.itinerary_continuity",
    )
    assert not any(module.startswith(forbidden_prefixes) for module in imports)


def test_final_document_sanitizer_cannot_reclassify_or_rebuild_itinerary_facts() -> None:
    imports = _imported_modules("itinerary_generation/final_document_sanitation.py")
    allowed_project_imports = {
        "itinerary_domain.field_sanitation",
        "itinerary_generation.render_model",
    }
    project_imports = {module for module in imports if module.startswith(("itinerary_domain", "itinerary_generation", "normalizer", "parser_modules"))}

    assert project_imports == allowed_project_imports
    forbidden_calls = {
        "parse_itinerary",
        "normalize_itinerary_rows",
        "build_itinerary_document",
        "build_render_document",
        "classify_product",
        "build_itinerary_continuity_report",
    }
    assert not (set(_call_names("itinerary_generation/final_document_sanitation.py")) & forbidden_calls)


def test_render_context_is_the_only_production_final_document_sanitation_call_site() -> None:
    call_sites: list[str] = []
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith("tests/") or relative == "itinerary_generation/final_document_sanitation.py":
            continue
        if "sanitize_prepared_render_document" in path.read_text(encoding="utf-8"):
            call_sites.append(relative)

    assert call_sites == ["app_modules/itinerary_render_context.py"]
    assert _call_names("app_modules/itinerary_render_context.py").count("sanitize_prepared_render_document") == 1


def test_preview_editor_pdf_renderers_do_not_apply_independent_customer_cleanup() -> None:
    renderer_paths = [
        "app_modules/render_final_sections_html.py",
        "ui/custom_final_pages.py",
        "ui/premium_final_notes.py",
        *[
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "pdf_exporter_modules").rglob("*.py")
        ],
    ]
    forbidden_modules = {
        "itinerary_domain.field_sanitation",
        "itinerary_generation.final_document_sanitation",
    }

    for relative in renderer_paths:
        assert not (_imported_modules(relative) & forbidden_modules), relative
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "sanitize_customer_field(" not in source, relative
        assert "sanitize_prepared_render_document(" not in source, relative
        assert "polish_client_text(" not in source, relative


def test_quality_gate_is_audit_only_and_does_not_call_mutating_sanitizers() -> None:
    relative = "itinerary_generation/client_output_quality_gate.py"
    source = (ROOT / relative).read_text(encoding="utf-8")
    calls = _call_names(relative)

    assert "sanitize_customer_field" not in source
    assert "sanitize_customer_html" not in source
    assert "sanitize_prepared_render_document" not in source
    assert not any(name.startswith("sanitize_") for name in calls)


def test_quality_text_traversal_is_explicit_and_excludes_internal_metadata() -> None:
    relative = "itinerary_generation/client_quality_text.py"
    source = (ROOT / relative).read_text(encoding="utf-8")
    traversed_fields = {
        node.args[1].value
        for node in ast.walk(_tree(relative))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    }

    assert "__dataclass_fields__" not in source
    assert not ({
        "continuity_report",
        "source_row_ids",
        "metadata",
        "background_path",
        "warnings",
        "labels",
        "css_class",
    } & traversed_fields)


def test_internal_url_and_provenance_fields_are_not_globally_erased() -> None:
    export_source = (ROOT / "calculator/workbook_export_plan.py").read_text(encoding="utf-8")
    generation_source = (ROOT / "app_modules/calculator_generation_rows.py").read_text(encoding="utf-8")
    final_source = (ROOT / "itinerary_generation/final_document_sanitation.py").read_text(encoding="utf-8")

    assert "source_url" in export_source
    assert "source_workbook" in export_source
    assert "source_sheet" in export_source
    assert "source_row" in export_source
    assert '"source_url": row.url' in generation_source
    assert "metadata" not in _call_names("itinerary_generation/final_document_sanitation.py")
    assert "technical metadata" in final_source.casefold()
