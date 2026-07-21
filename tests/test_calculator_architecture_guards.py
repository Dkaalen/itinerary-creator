import ast
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


def test_workbook_package_renderer_has_split_responsibility_owners() -> None:
    package_source = (ROOT / "calculator" / "workbook_package_export.py").read_text(encoding="utf-8")
    changes_source = (ROOT / "calculator" / "workbook_package_cell_changes.py").read_text(encoding="utf-8")
    worksheet_source = (ROOT / "calculator" / "workbook_worksheet_xml.py").read_text(encoding="utf-8")
    recalculation_source = (ROOT / "calculator" / "workbook_recalculation_xml.py").read_text(encoding="utf-8")
    zip_source = (ROOT / "calculator" / "workbook_zip_package.py").read_text(encoding="utf-8")

    assert "generate_cell_changes" in changes_source
    assert "patch_worksheet_xml" in worksheet_source
    assert "<sheetData>" in worksheet_source
    assert "patch_workbook_calculation_properties" in recalculation_source
    assert "<calcPr" in recalculation_source
    assert "clone_xlsx_package" in zip_source
    assert "ZipInfo" in zip_source

    for imported_name in (
        "generate_cell_changes",
        "patch_worksheet_xml",
        "patch_workbook_calculation_properties",
        "clone_xlsx_package",
    ):
        assert imported_name in package_source
    assert "re.compile" not in package_source
    assert "<sheetData>" not in package_source
    assert "<calcPr" not in package_source
    assert "ZipInfo" not in package_source


def test_cross_workflow_state_keys_have_one_literal_authority() -> None:
    key_source = (ROOT / "app_modules" / "session_state_keys.py").read_text(encoding="utf-8")
    assert 'ACTIVE_APP_PAGE_KEY = "active_app_page"' in key_source
    assert 'APP_STAGE_KEY = "app_stage"' in key_source
    assert 'ACTIVE_SAVED_PROJECT_KEY = "active_saved_project"' in key_source

    guarded_roots = (ROOT / "app_modules", ROOT / "project_storage")
    protected_literals = (
        "active_app_page",
        "app_stage",
        "active_saved_project",
        "active_saved_project_id",
        "active_project_storage_id",
        "project_storage_last_saved_snapshot_path",
        "project_storage_last_error",
        "project_storage_last_error_detail",
        "project_storage_browser_success",
        "project_storage_delete_cleanup_warning",
    )
    offenders = []
    for guarded_root in guarded_roots:
        for path in guarded_root.glob("*.py"):
            if path.name == "session_state_keys.py":
                continue
            source = path.read_text(encoding="utf-8")
            for literal in protected_literals:
                if f'"{literal}"' in source or f"'{literal}'" in source:
                    offenders.append(f"{path.relative_to(ROOT)}:{literal}")
    assert offenders == []


def test_cross_workflow_transitions_are_named_and_ui_independent() -> None:
    source = (ROOT / "app_modules" / "session_transitions.py").read_text(encoding="utf-8")
    for function_name in (
        "begin_local_calculator_import",
        "complete_calculator_generation",
        "fail_calculator_generation",
        "complete_saved_project_open",
        "return_to_calculator",
        "prepare_project_switch",
        "complete_project_duplicate",
        "complete_project_delete",
        "record_failed_save",
    ):
        assert f"def {function_name}(" in source
    assert "import streamlit" not in source


def test_session_state_ownership_document_names_transition_authorities() -> None:
    text = (ROOT / "docs" / "SESSION_STATE_OWNERSHIP.md").read_text(encoding="utf-8")
    assert "session_state_keys.py" in text
    assert "session_transitions.py" in text
    assert "Saved-project opening is transactional" in text


def test_browser_grid_is_the_only_production_autocomplete_authority() -> None:
    index_source = (ROOT / "calculator_grid_component" / "frontend" / "index.html").read_text(encoding="utf-8")
    payload_source = (ROOT / "app_modules" / "calculator_component_payload.py").read_text(encoding="utf-8")
    page_source = (ROOT / "app_modules" / "calculator_page.py").read_text(encoding="utf-8")
    library_source = (FRONTEND / "calculator_grid_library.js").read_text(encoding="utf-8")
    suggestion_source = (FRONTEND / "calculator_grid_suggestions.js").read_text(encoding="utf-8")

    library_script = '<script src="js/calculator_grid_library.js"></script>'
    suggestion_script = '<script src="js/calculator_grid_suggestions.js"></script>'
    assert library_script in index_source
    assert suggestion_script in index_source
    assert index_source.index(library_script) < index_source.index(suggestion_script)
    assert '"library_rows": _cached_library_rows' in payload_source
    assert '"library_ranking_spec": local_library_ranking_spec_payload()' in payload_source
    assert "render_calculator_grid" in page_source
    assert "function findLibrarySuggestions(" in library_source
    assert "rankingSpec.search_fields" in library_source
    assert "const fieldWeights =" not in library_source
    assert "sheet_exact: 1400" not in library_source
    assert "function applyLibrarySuggestion(" in library_source
    assert "function scheduleSuggestions(" in suggestion_source
    assert "function applySuggestion(" in suggestion_source


def test_retired_python_autocomplete_compatibility_modules_are_absent() -> None:
    retired_paths = (
        ROOT / "calculator" / "fetch_lines.py",
        ROOT / "calculator" / "grid_autocomplete.py",
    )
    assert [path for path in retired_paths if path.exists()] == []

    production_imports = []
    for root in (ROOT / "app_modules", ROOT / "calculator"):
        for path in root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            if "calculator.fetch_lines" in source or "calculator.grid_autocomplete" in source:
                production_imports.append(str(path.relative_to(ROOT)))
    assert production_imports == []


def test_calculator_architecture_document_names_autocomplete_authority() -> None:
    text = (ROOT / "docs" / "CALCULATOR_ARCHITECTURE.md").read_text(encoding="utf-8")
    ranking_text = (ROOT / "docs" / "LOCAL_LIBRARY_RANKING.md").read_text(encoding="utf-8")
    assert "## Local Library autocomplete" in text
    assert "calculator/library_ranking.py` owns" in text
    assert "production browser execution authority" in text
    assert "not supported compatibility surfaces" in text
    assert "Norway in a Nutshell" in ranking_text
    assert "Intentional duplicate rows remain separate" in ranking_text

def test_financial_rule_ownership_is_versioned_and_cross_boundary() -> None:
    rules_source = (ROOT / "calculator" / "financial_rules.py").read_text(encoding="utf-8")
    payload_source = (ROOT / "app_modules" / "calculator_component_payload.py").read_text(encoding="utf-8")
    math_source = (FRONTEND / "calculator_grid_math.js").read_text(encoding="utf-8")
    state_source = (FRONTEND / "calculator_grid_state_controller.js").read_text(encoding="utf-8")
    action_source = (FRONTEND / "calculator_grid_actions.js").read_text(encoding="utf-8")

    assert 'FINANCIAL_RULES_VERSION = "financial-v1"' in rules_source
    assert '"margin_basis": "net_price_nok"' in rules_source
    assert '"financial_rules": financial_rules_payload()' in payload_source
    assert "function setActiveFinancialRules(" in math_source
    assert "salesPricePerUnitForMargin(" in math_source
    assert "setActiveFinancialRules(payload.financial_rules" in state_source
    assert "evaluator.salesPricePerUnitForMargin(" in action_source
    assert "activeFinancialRules.sales_price_derived_override_fields" in action_source


def test_excel_import_and_export_share_financial_precision_contract() -> None:
    export_source = (ROOT / "calculator" / "workbook_export_plan.py").read_text(encoding="utf-8")
    import_source = (ROOT / "calculator" / "workbook_import.py").read_text(encoding="utf-8")
    formula_source = (ROOT / "calculator" / "formula_map.py").read_text(encoding="utf-8")

    assert "from calculator.financial_rules import canonical_export_value" in export_source
    assert "canonical_export_value(field_name" in export_source
    assert "from calculator.financial_rules import unwrap_canonical_export_formula" in import_source
    assert "unwrap_canonical_export_formula(" in import_source
    assert '=ROUND(SUM(' in formula_source


def test_calculator_architecture_document_names_financial_authority() -> None:
    architecture = (ROOT / "docs" / "CALCULATOR_ARCHITECTURE.md").read_text(encoding="utf-8")
    rules = (ROOT / "docs" / "CALCULATOR_FINANCIAL_RULES.md").read_text(encoding="utf-8")

    assert "## Financial parity" in architecture
    assert "actual `net_price_nok`" in architecture
    assert "Excel export/import preserve financial inputs" in architecture
    assert "single versioned contract" in rules
    assert "Target GP margin shortcuts" in rules
    assert "app-generated wrapper" in rules

def test_calculator_browser_workflows_are_bounded_and_share_one_harness() -> None:
    browser_test_paths = (
        ROOT / "tests" / "test_calculator_browser_editing_and_caret.py",
        ROOT / "tests" / "test_calculator_browser_navigation_and_focus.py",
        ROOT / "tests" / "test_calculator_browser_clipboard_and_paste.py",
        ROOT / "tests" / "test_calculator_browser_autocomplete_and_fetching.py",
        ROOT / "tests" / "test_calculator_browser_formulas_and_currencies.py",
        ROOT / "tests" / "test_calculator_browser_download_and_import.py",
        ROOT / "tests" / "test_calculator_browser_component_lifecycle_and_messaging.py",
        ROOT / "tests" / "test_calculator_browser_drafts_and_recovery.py",
    )
    retired_paths = (
        ROOT / "tests" / "test_calculator_browser_interactions.py",
        ROOT / "tests" / "test_calculator_browser_recovery.py",
    )

    assert all(path.exists() for path in browser_test_paths)
    assert all(not path.exists() for path in retired_paths)

    collected_names: list[str] = []
    for path in browser_test_paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        test_names = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        ]
        assert 1 <= len(test_names) <= 10
        assert "sync_playwright" not in source
        assert "calculator_browser_harness" in source
        collected_names.extend(test_names)

    assert len(collected_names) == 43
    assert len(set(collected_names)) == 43

    harness_source = (ROOT / "tests" / "support" / "calculator_browser_harness.py").read_text(encoding="utf-8")
    assert "def calculator_frontend_html(" in harness_source
    assert "def open_blank_calculator_browser_page(" in harness_source
    assert "def open_calculator_browser_page(" in harness_source
    assert "def open_recovery_browser_page(" in harness_source
    assert "def install_storage_quota(" in harness_source


def test_calculator_architecture_document_names_bounded_browser_groups() -> None:
    text = (ROOT / "docs" / "CALCULATOR_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "### Bounded Chromium workflows" in text
    assert "editing and caret behavior" in text
    assert "component lifecycle and messaging" in text
    assert "tests/support/calculator_browser_harness.py" in text
