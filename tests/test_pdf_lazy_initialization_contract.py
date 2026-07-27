from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

import pdf_exporter


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PDF_API = (
    "PdfExportProfile",
    "PdfExportResult",
    "create_pdf",
    "pdf_export_profile_options",
    "pdf_filename",
    "resolve_pdf_export_profile",
)
LAZY_SCENARIOS = (
    "app_modules.streamlit_entry",
    "app_modules.route_registry",
    "app_modules.calculator_page",
    "itinerary_parser",
    "normalizer",
    "generator",
    "app_modules.preview_step",
    "visual_editor_component.editor_workflow",
    "app_modules.picture_step",
    "app_modules.export_page",
    "app_modules.export_actions",
)
HEAVY_IMPLEMENTATION_MODULES = {
    "pdf_exporter_modules.exporter",
    "pdf_exporter_modules.typed_exporter",
    "pdf_exporter_modules.styles",
    "pdf_exporter_modules.render_content",
    "pdf_exporter_modules.render_cover",
    "pdf_exporter_modules.render_glance",
}


def _clean_probe(body: str, *arguments: str) -> dict[str, object]:
    prelude = textwrap.dedent(
        f"""
        import json
        import sys
        from pathlib import Path
        root = Path({str(ROOT)!r})
        sys.path.insert(0, str(root))
        sys.path.insert(0, str(root / "tests"))
        from support.streamlit_stub import install_streamlit_stub
        install_streamlit_stub(force=True)
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", prelude + "\n" + textwrap.dedent(body), *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return json.loads(completed.stdout)


def test_supported_pdf_api_and_private_package_initializer_are_explicit() -> None:
    import pdf_exporter_modules

    assert tuple(pdf_exporter.__all__) == SUPPORTED_PDF_API
    assert tuple(pdf_exporter_modules.__all__) == ()
    assert not (ROOT / "pdf_exporter_modules" / "public_api.py").exists()


def test_application_workflows_do_not_initialize_pdf_engine() -> None:
    for module_name in LAZY_SCENARIOS:
        result = _clean_probe(
            """
            import importlib
            import sys

            importlib.import_module(sys.argv[1])
            reportlab = sorted(
                name for name in sys.modules
                if name == "reportlab" or name.startswith("reportlab.")
            )
            heavy_pdf = sorted(set(sys.modules).intersection(%r))
            print(json.dumps({"reportlab": reportlab, "heavy_pdf": heavy_pdf}))
            """ % HEAVY_IMPLEMENTATION_MODULES,
            module_name,
        )
        assert result == {"reportlab": [], "heavy_pdf": []}, module_name


def test_pdf_engine_initializes_only_when_pdf_creation_begins() -> None:
    result = _clean_probe(
        """
        import sys
        import tempfile
        from pathlib import Path
        import pdf_exporter

        before = any(name == "reportlab" or name.startswith("reportlab.") for name in sys.modules)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "preview.html"
            pdf_path = root / "preview.pdf"
            html_path.write_text(
                '<html><body><div class="a4-page"><p>Lazy PDF probe</p></div></body></html>',
                encoding="utf-8",
            )
            export_result = pdf_exporter.create_pdf(html_path, pdf_path)
            payload = {
                "before": before,
                "after": any(name == "reportlab" or name.startswith("reportlab.") for name in sys.modules),
                "status": export_result.status,
                "renderer": export_result.renderer,
                "exists": bool(export_result.path and export_result.path.exists()),
                "size": export_result.path.stat().st_size if export_result.path else 0,
            }
        print(json.dumps(payload))
        """
    )
    assert result["before"] is False
    assert result["after"] is True
    assert result["status"] == "created"
    assert result["renderer"] == "html"
    assert result["exists"] is True
    assert int(result["size"]) > 0


@pytest.mark.parametrize("dependency", ("reportlab", "PIL", "bs4"))
def test_missing_pdf_dependency_returns_supported_failure(
    monkeypatch,
    tmp_path: Path,
    dependency: str,
) -> None:
    html_path = tmp_path / "preview.html"
    html_path.write_text('<div class="a4-page">Preview</div>', encoding="utf-8")
    real_import = importlib.import_module

    def blocked_import(module_name: str):
        if module_name == "pdf_exporter_modules.exporter":
            error = ModuleNotFoundError(f"No module named '{dependency}'")
            error.name = dependency
            raise error
        return real_import(module_name)

    monkeypatch.setattr(pdf_exporter, "_import_module", blocked_import)
    result = pdf_exporter.create_pdf(html_path, tmp_path / "preview.pdf")

    assert result.status == "dependency_unavailable"
    assert result.error_code == "pdf_dependency_unavailable"
    assert result.dependency == dependency
    assert result.path is None
    assert "preview was not changed" in result.message


def test_invalid_pdf_request_stays_lightweight(tmp_path: Path) -> None:
    before = set(sys.modules)
    result = pdf_exporter.create_pdf(tmp_path / "missing.html", tmp_path / "missing.pdf")
    newly_loaded = set(sys.modules) - before

    assert result.status == "invalid_request"
    assert not any(name == "reportlab" or name.startswith("reportlab.") for name in newly_loaded)


def test_production_code_uses_only_supported_pdf_api() -> None:
    production_roots = (
        ROOT / "app.py",
        ROOT / "app_modules",
        ROOT / "calculator",
        ROOT / "images",
        ROOT / "itinerary_domain",
        ROOT / "itinerary_generation",
        ROOT / "normalizer_modules",
        ROOT / "parser_modules",
        ROOT / "project_storage",
        ROOT / "shared",
        ROOT / "text_polish_modules",
        ROOT / "ui",
        ROOT / "visual_editor_component",
    )
    offenders: list[str] = []
    for root in production_roots:
        files = (root,) if root.is_file() else tuple(root.rglob("*.py"))
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.Import):
                    imported = {alias.name for alias in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported = {node.module}
                else:
                    continue
                if any(name == "pdf_exporter_modules" or name.startswith("pdf_exporter_modules.") for name in imported):
                    offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []
    assert "from pdf_exporter import create_pdf" in (ROOT / "ui" / "export_files.py").read_text(encoding="utf-8")
