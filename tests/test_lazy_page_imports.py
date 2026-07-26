"""Import-boundary checks for Streamlit page routing."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
PAGE_MODULES = (
    "app_modules.calculator_page",
    "app_modules.local_library_page",
    "app_modules.input_step",
    "app_modules.preview_step",
    "app_modules.picture_step",
    "app_modules.export_page",
)


def _run_clean_import(body: str) -> subprocess.CompletedProcess[str]:
    prelude = textwrap.dedent(
        f"""
        import sys
        from pathlib import Path
        root = Path({str(ROOT)!r})
        sys.path.insert(0, str(root))
        sys.path.insert(0, str(root / "tests"))
        from support.streamlit_stub import install_streamlit_stub
        install_streamlit_stub(force=True)
        """
    )
    script = prelude + "\n" + textwrap.dedent(body)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "tests")))
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_main_view_routes_before_importing_page_renderers() -> None:
    imports = _top_level_imports(ROOT / "app_modules" / "main_view.py")
    assert imports.isdisjoint(PAGE_MODULES)
    assert "app_modules.debug_tools" not in imports

    result = _run_clean_import(
        """
        import sys
        import app_modules.main_view
        forbidden = {
            "app_modules.calculator_page",
            "app_modules.local_library_page",
            "app_modules.input_step",
            "app_modules.preview_step",
            "app_modules.picture_step",
            "app_modules.export_page",
            "app_modules.debug_tools",
        }
        loaded = sorted(forbidden.intersection(sys.modules))
        if loaded:
            raise SystemExit(f"router eagerly imported: {loaded}")
        """
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_calculator_import_excludes_unrelated_itinerary_systems() -> None:
    result = _run_clean_import(
        """
        import sys
        import app_modules.calculator_page
        forbidden_exact = {
            "app_modules.calculator_generation_action",
            "app_modules.generation_action",
            "app_modules.validation_gate",
            "app_modules.input_step",
            "app_modules.preview_step",
            "app_modules.picture_step",
            "app_modules.export_page",
        }
        loaded = sorted(forbidden_exact.intersection(sys.modules))
        loaded += sorted(
            name for name in sys.modules
            if name.startswith(("visual_editor_component.", "pdf_exporter_modules."))
        )
        loaded += sorted(
            name for name in sys.modules
            if name.startswith("itinerary_generation.")
            and name != "itinerary_generation.tone_presets"
        )
        if loaded:
            raise SystemExit(f"calculator imported unrelated systems: {loaded}")
        """
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_major_page_modules_import_independently() -> None:
    for module_name in PAGE_MODULES:
        result = _run_clean_import(f"import {module_name}")
        assert result.returncode == 0, f"{module_name}: {result.stderr or result.stdout}"


def test_page_imports_do_not_pull_unrelated_registered_surfaces() -> None:
    expected_loaded = {
        "app_modules.calculator_page": {"app_modules.calculator_page"},
        "app_modules.local_library_page": {"app_modules.local_library_page"},
        "app_modules.input_step": {"app_modules.input_step"},
        "app_modules.preview_step": {"app_modules.preview_step"},
        "app_modules.picture_step": {"app_modules.picture_step", "app_modules.preview_step"},
        "app_modules.export_page": {"app_modules.export_page", "app_modules.preview_step"},
    }

    for module_name, expected in expected_loaded.items():
        result = _run_clean_import(
            f"""
            import sys
            import {module_name}
            registered = {set(PAGE_MODULES)!r}
            loaded = registered.intersection(sys.modules)
            expected = {expected!r}
            if loaded != expected:
                raise SystemExit(f"unexpected registered page imports: {{sorted(loaded)}}")
            """
        )
        assert result.returncode == 0, f"{module_name}: {result.stderr or result.stdout}"


def test_app_bootstrap_delegates_to_the_single_lazy_entry_boundary() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "from app_modules.streamlit_entry import run_streamlit_app" in source
    assert "run_streamlit_app()" in source
    assert "import streamlit" not in source
    assert "app_modules.project_io" not in source
    assert "app_modules.main_view" not in source
