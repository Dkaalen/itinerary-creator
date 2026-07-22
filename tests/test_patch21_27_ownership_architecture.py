"""Ownership and compatibility guards for the Patch 21-27 architecture."""
from __future__ import annotations

from pathlib import Path

from calculator.library_workbook import load_local_library_workbook
from itinerary_generation.day_intro_writer import write_day_intro
from itinerary_generation.destination_content import destination_copy
from itinerary_generation.summaries_experience import describe_city_experience
from itinerary_generation.transport_domain.route_points import get_route_points_for_transport
from scripts.test_group_hygiene import build_report
from scripts.test_groups import GROUPS

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "calculator_grid_component" / "frontend"
JS = FRONTEND / "js"


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _owner_files(function_name: str) -> list[str]:
    signature = f"function {function_name}("
    return sorted(path.name for path in JS.glob("*.js") if signature in path.read_text(encoding="utf-8"))


def test_calculator_frontend_has_one_owner_per_split_responsibility() -> None:
    expected = {
        "setCellEditingMode": "calculator_grid_caret.js",
        "handleCellInput": "calculator_grid_cell_commits.js",
        "updateActiveCellFromFormulaBar": "calculator_grid_formula_sync.js",
        "handleCellKeydown": "calculator_grid_keyboard.js",
        "calculateCurrencyExposure": "calculator_grid_currency.js",
        "formatNumber": "calculator_grid_formatting.js",
        "buildToolbarHtml": "calculator_grid_toolbar_render.js",
        "buildTableHtml": "calculator_grid_grid_render.js",
        "refreshValidationAndStatus": "calculator_grid_status_render.js",
        "buildSuggestionHtml": "calculator_grid_suggestion_render.js",
        "handleExcelFileSelection": "calculator_grid_excel_actions.js",
        "applySalesMargin": "calculator_grid_sales_actions.js",
        "submitAction": "calculator_grid_submission_actions.js",
        "handleGlobalCalculatorShortcut": "calculator_grid_shortcuts.js",
    }
    for function_name, owner in expected.items():
        assert _owner_files(function_name) == [owner]


def test_calculator_frontend_load_order_is_deterministic() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    scripts = [line.split('src="', 1)[1].split('"', 1)[0] for line in html.splitlines() if '<script src="' in line]
    positions = {Path(script).name: index for index, script in enumerate(scripts)}

    assert positions["calculator_grid_math.js"] < positions["calculator_grid_currency.js"]
    assert positions["calculator_grid_currency.js"] < positions["calculator_grid_render.js"]
    assert positions["calculator_grid_toolbar_render.js"] < positions["calculator_grid_render.js"]
    assert positions["calculator_grid_caret.js"] < positions["calculator_grid_cell_editing.js"]
    assert positions["calculator_grid_submission_actions.js"] < positions["calculator_grid_actions.js"]
    assert positions["calculator_grid_actions.js"] < positions["calculator_grid_app.js"]
    assert len(scripts) == len(set(scripts))


def test_generation_facades_delegate_to_distinct_owners() -> None:
    day_facade = _source("itinerary_generation/day_intro_writer.py")
    destination_facade = _source("itinerary_generation/destination_content.py")
    summary_facade = _source("itinerary_generation/summaries_experience.py")

    assert "from itinerary_generation.day_intro_rendering import" in day_facade
    assert "def write_day_intro(" not in day_facade
    assert "from itinerary_generation.destination_content_lookup import resolve_destination" in destination_facade
    assert "from itinerary_generation.destination_leisure_content import" in destination_facade
    assert "from itinerary_generation.summaries_experience_signals import" in summary_facade
    assert "deduplicate_candidates" in summary_facade


def test_route_and_workbook_facades_preserve_behavior() -> None:
    route = get_route_points_for_transport(
        {"effective_type": "Train", "title": "Train: Oslo to Bergen", "city": "Oslo"}
    )
    assert route == ("Oslo", "Bergen")

    workbook = load_local_library_workbook()
    assert len(workbook.rows) > 5_000
    assert workbook.currency_rates
    assert workbook.fingerprint


def test_destination_and_experience_public_copy_remains_available() -> None:
    oslo = destination_copy("Oslo")
    assert oslo.arc
    assert oslo.arrival_focus
    assert oslo.leisure_options

    phrase = describe_city_experience(
        [{"effective_type": "Activity", "title": "Guided walking tour", "city": "Oslo"}]
    )
    assert phrase
    assert callable(write_day_intro)


def test_all_test_modules_are_grouped_with_browser_workflows_explicit() -> None:
    report = build_report()
    assert report["full_only_test_module_count"] == 0
    assert report["stale_group_entry_count"] == 0
    assert report["duplicate_group_entry_count"] == 0
    browser_workflows = GROUPS["calculator-browser"]
    assert browser_workflows
    assert all("::test_" in node for node in browser_workflows)
    assert len(browser_workflows) == len(set(browser_workflows))
