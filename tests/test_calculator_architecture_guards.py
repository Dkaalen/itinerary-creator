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
    plan_source = (ROOT / "calculator" / "workbook_export_plan.py").read_text(encoding="utf-8")
    renderer_source = (ROOT / "calculator" / "workbook_export.py").read_text(encoding="utf-8")
    assert "expected_row_formulas" in plan_source
    assert "TOTAL_FORMULAS" in plan_source
    assert "VLOOKUP(" not in plan_source
    assert "VLOOKUP(" not in renderer_source


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


def test_workbook_renderers_consume_one_canonical_export_plan() -> None:
    plan_source = (ROOT / "calculator" / "workbook_export_plan.py").read_text(encoding="utf-8")
    openpyxl_source = (ROOT / "calculator" / "workbook_export.py").read_text(encoding="utf-8")
    package_source = (ROOT / "calculator" / "workbook_package_export.py").read_text(encoding="utf-8")
    import_source = (ROOT / "calculator" / "workbook_import.py").read_text(encoding="utf-8")

    assert "ROW_VALUE_COLUMNS" in plan_source
    assert "FORMULA_FIELD_BY_COLUMN" in plan_source
    assert "build_workbook_export_plan" in openpyxl_source
    assert "WorkbookExportPlan" in package_source
    assert "CalculatorState" not in package_source
    assert "_ROW_VALUE_COLUMNS = {" not in openpyxl_source
    assert "_ROW_VALUE_COLUMNS = {" not in package_source
    assert "from calculator.workbook_export_plan import" in import_source
