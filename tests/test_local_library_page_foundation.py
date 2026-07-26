from __future__ import annotations

from pathlib import Path

from tests.support.static_contracts import read_contract_text


def test_local_library_page_is_registered_and_routed_from_main_view() -> None:
    from app_modules.route_registry import DIRECT_PAGE_ROUTE_SPECS, LOCAL_LIBRARY_PAGE

    main_view = read_contract_text("app_modules/main_view.py")
    route = DIRECT_PAGE_ROUTE_SPECS[LOCAL_LIBRARY_PAGE]

    assert route.module_name == "app_modules.local_library_page"
    assert route.renderer_name == "render_local_library_page"
    assert "route_spec_for" in main_view
    assert "_load_route_renderer" in main_view


def test_calculator_page_exposes_manage_local_library_button() -> None:
    calculator_page = read_contract_text("app_modules/calculator_page.py")
    calculator_actions = read_contract_text("app_modules/calculator_page_actions.py")

    assert "Manage Local Library" in calculator_page
    assert "open_local_library_page" in calculator_actions


def test_local_library_page_is_read_only_and_explains_workbook_maintenance() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "app_modules/local_library_page.py",
            "app_modules/local_library_browser_ui.py",
            "app_modules/local_library_status_ui.py",
        )
    )

    assert "Back to itinerary calculator" in sources
    assert "bundled Excel workbook" in sources
    assert "Edit the workbook and redeploy" in sources
    assert "Refresh Local Library" in sources
    assert "Advanced diagnostics" in sources
    assert "Save Local Library row" not in sources
    assert "Remove Local Library row" not in sources
    assert "st.form" not in sources


def test_local_library_browser_has_required_filters_and_bounded_results() -> None:
    browser = read_contract_text("app_modules/local_library_browser_ui.py")

    for label in ("Worksheet", "Country", "City", "Type", "Supplier", "Currency"):
        assert f'"{label}"' in browser
    assert "Rows per page" in browser
    assert "Record details" in browser
    assert "source_sheet" in browser
    assert "source_row" in browser


def test_local_library_page_is_split_by_responsibility() -> None:
    page = read_contract_text("app_modules/local_library_page.py")

    assert "render_local_library_source_status" in page
    assert "render_local_library_browser" in page
    assert "LocalLibraryStore" not in page
    assert "st.form" not in page
