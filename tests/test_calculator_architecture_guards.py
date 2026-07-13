from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "calculator_grid_component" / "frontend" / "js"


def test_calculation_ownership_is_explicit() -> None:
    frontend_definitions = []
    for path in FRONTEND.glob("*.js"):
        if "function calculateRow(" in path.read_text(encoding="utf-8"):
            frontend_definitions.append(path.name)
    assert frontend_definitions == ["calculator_grid_math.js"]

    python_sources = list((ROOT / "calculator").glob("*.py"))
    backend_definitions = [path.name for path in python_sources if "def calculate_row(" in path.read_text(encoding="utf-8")]
    assert backend_definitions == ["calculations.py"]


def test_export_uses_formula_map_instead_of_a_parallel_formula_engine() -> None:
    export_source = (ROOT / "calculator" / "workbook_export.py").read_text(encoding="utf-8")
    assert "expected_row_formulas" in export_source
    assert "TOTAL_FORMULAS" in export_source
    assert "VLOOKUP(" not in export_source


def test_project_management_domain_module_is_ui_independent() -> None:
    source = (ROOT / "project_storage" / "project_management.py").read_text(encoding="utf-8")
    assert "import streamlit" not in source
    assert "def rename_project" in source
    assert "def duplicate_project" in source


def test_calculator_architecture_document_names_state_boundaries() -> None:
    text = (ROOT / "docs" / "CALCULATOR_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "authoritative financial engine" in text
    assert "Selection mode" in text
    assert "Save → reload → recalculate" in text
