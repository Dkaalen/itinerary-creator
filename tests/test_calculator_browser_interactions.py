from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1] / "calculator_grid_component" / "frontend"


def _html() -> str:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "styles" / "calculator_grid.css").read_text(encoding="utf-8")
    scripts = "".join(
        f"<script>{(ROOT / source).read_text(encoding='utf-8')}</script>"
        for source in re.findall(r'<script src="([^"]+)"', index)
    )
    storage = """<script>
      (() => {
        const store = new Map();
        Object.defineProperty(window, 'localStorage', {value: {
          getItem: (key) => store.has(String(key)) ? store.get(String(key)) : null,
          setItem: (key, value) => store.set(String(key), String(value)),
          removeItem: (key) => store.delete(String(key)),
          clear: () => store.clear()
        }});
      })();
    </script>"""
    return f"<html><head><style>{css}</style></head><body><div id='root'></div>{storage}{scripts}</body></html>"


def _payload(rows: list[dict], *, library_rows: list[dict] | None = None, revision: str = "browser-test") -> dict:
    return {
        "rows": rows,
        "number_of_pax": None,
        "state_revision": revision,
        "draft_storage_key": f"calculator.browser.test.{revision}",
        "show_advanced": False,
        "currency_rates": {"NOK": 1, "EUR": 12},
        "library_status": "Ready",
        "library_rows": library_rows or [],
    }


def _browser_page(payload: dict):
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.set_content(_html(), wait_until="load")
    page.evaluate(
        "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
        payload,
    )
    page.wait_for_selector('td[data-key="travel_element"]')
    return manager, browser, page


def test_first_click_on_prefilled_cell_enables_immediate_arrow_navigation() -> None:
    manager, browser, page = _browser_page(
        _payload([{"row_id": "1", "travel_element": "Fetched hotel", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1}])
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.press("ArrowRight")

        assert page.evaluate("document.activeElement.dataset.key") == "url"
        assert page.evaluate("activeCellEditing") is False
    finally:
        browser.close()
        manager.stop()


def test_arrow_keys_move_inside_text_only_while_cell_is_being_edited() -> None:
    manager, browser, page = _browser_page(
        _payload([{"row_id": "1", "travel_element": "Central Hotel", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1}], revision="caret")
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        cell.click()
        page.keyboard.press("End")
        page.keyboard.press("ArrowLeft")

        assert page.evaluate("activeCellEditing") is True
        assert page.evaluate("document.activeElement.dataset.key") == "travel_element"
        assert page.evaluate("window.getSelection().anchorOffset") == len("Central Hotel") - 1

        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.dataset.key") == "url"
        assert page.evaluate("activeCellEditing") is False
    finally:
        browser.close()
        manager.stop()


def test_fetched_suggestion_returns_focus_to_grid_navigation_mode() -> None:
    library_row = {
        "library_id": "hotel-1",
        "label": "Fetched Hotel",
        "preview": "Hotel in Oslo",
        "travel_element": "Fetched Hotel",
        "supplier": "Supplier",
        "country": "Norway",
        "category": "Hotel",
        "type": "Hotel",
        "comments": "",
        "search_text": "fetched hotel",
        "url": "",
        "row_data": {
            "row_id": "",
            "type": "Hotel",
            "travel_element": "Fetched Hotel",
            "supplier": "Supplier",
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
            "gross_price_per_unit": 100,
            "units": 1,
        },
    }
    manager, browser, page = _browser_page(
        _payload([{"row_id": "1", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": "", "units": ""}], library_rows=[library_row], revision="suggestion")
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.type("Fetched")
        page.locator(".suggestion-item").wait_for(timeout=3000)
        page.locator(".suggestion-item").click()

        assert cell.text_content().strip() == "Fetched Hotel"
        assert page.evaluate("activeCellEditing") is False
        page.keyboard.press("ArrowRight")
        assert page.evaluate("document.activeElement.dataset.key") == "url"
    finally:
        browser.close()
        manager.stop()


def test_find_replace_and_selected_row_actions_work_in_the_rendered_grid() -> None:
    rows = [
        {"row_id": "1", "travel_element": "Hotel Alpha", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1},
        {"row_id": "2", "travel_element": "Hotel Beta", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 200, "units": 1},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="advanced"))
    try:
        page.locator('td[data-row-index="0"][data-key="travel_element"]').click()
        page.get_by_role("button", name="Duplicate selected rows").click()
        assert page.locator("tr.calc-row").count() == 3

        page.get_by_role("button", name="Find / replace").click()
        page.get_by_label("Find").fill("Hotel")
        page.get_by_label("Replace with").fill("Lodge")
        page.get_by_role("button", name="Replace all").click()

        values = page.locator('td[data-key="travel_element"]').all_text_contents()
        assert values == ["Lodge Alpha", "Lodge Alpha", "Lodge Beta"]
    finally:
        browser.close()
        manager.stop()


def test_rectangular_paste_fill_and_undo_redo_behave_like_a_grid() -> None:
    rows = [
        {"row_id": "1", "travel_element": "Source", "url": "https://one.example", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1},
        {"row_id": "2", "travel_element": "Target", "url": "", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 200, "units": 1},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="paste-fill-history"))
    try:
        first = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        second = page.locator('td[data-row-index="1"][data-key="travel_element"]')
        first.click()
        second.click(modifiers=["Shift"])
        page.get_by_role("button", name="Fill down").click()
        assert second.text_content().strip() == "Source"

        first.click()
        page.evaluate(
            """text => {
                const data = new DataTransfer();
                data.setData('text/plain', text);
                document.dispatchEvent(new ClipboardEvent('paste', {clipboardData: data, bubbles: true}));
            }""",
            "Alpha\thttps://alpha.example\nBeta\thttps://beta.example",
        )
        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Alpha"
        assert page.locator('td[data-row-index="0"][data-key="url"]').text_content().strip() == "https://alpha.example"
        assert page.locator('td[data-row-index="1"][data-key="travel_element"]').text_content().strip() == "Beta"
        assert page.locator('td[data-row-index="1"][data-key="url"]').text_content().strip() == "https://beta.example"

        page.keyboard.press("Control+z")
        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Source"
        page.keyboard.press("Control+y")
        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Alpha"
    finally:
        browser.close()
        manager.stop()


def test_row_insert_delete_and_column_resize_work_in_rendered_grid() -> None:
    rows = [
        {"row_id": "1", "travel_element": "Alpha", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1},
        {"row_id": "2", "travel_element": "Beta", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 200, "units": 1},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="rows-resize"))
    try:
        page.locator('td[data-row-index="0"][data-key="travel_element"]').click()
        page.get_by_role("button", name="Insert below").click()
        assert page.locator("tr.calc-row").count() == 3
        assert page.locator('td[data-row-index="1"][data-key="travel_element"]').text_content().strip() == ""

        page.locator('td[data-row-index="1"][data-key="travel_element"]').click()
        page.get_by_role("button", name="Delete selected rows").click()
        assert page.locator("tr.calc-row").count() == 2
        assert page.locator('td[data-row-index="1"][data-key="travel_element"]').text_content().strip() == "Beta"

        header = page.locator('th[data-column-key="travel_element"]')
        handle = header.locator('.column-resize-handle')
        before = header.bounding_box()["width"]
        box = handle.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2 + 70, box["y"] + box["height"] / 2)
        page.mouse.up()
        after = page.locator('th[data-column-key="travel_element"]').bounding_box()["width"]
        assert after >= before + 50
    finally:
        browser.close()
        manager.stop()


def test_drag_fill_handle_copies_selected_cell_downward() -> None:
    rows = [
        {"row_id": "1", "travel_element": "Repeated service", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1},
        {"row_id": "2", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="drag-fill"))
    try:
        source = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        target = page.locator('td[data-row-index="1"][data-key="travel_element"]')
        source.click()
        handle = source.locator('.fill-handle')
        handle.wait_for()
        handle_box = handle.bounding_box()
        target_box = target.bounding_box()
        page.mouse.move(handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
        page.mouse.down()
        page.mouse.move(target_box["x"] + target_box["width"] / 2, target_box["y"] + target_box["height"] / 2, steps=6)
        page.mouse.up()

        assert target.text_content().strip() == "Repeated service"
    finally:
        browser.close()
        manager.stop()


def test_selecting_prefilled_library_cell_does_not_open_suggestions_or_steal_arrows() -> None:
    library_row = {
        "library_id": "hotel-prefilled",
        "label": "Fetched Hotel",
        "preview": "Hotel in Oslo",
        "travel_element": "Fetched Hotel",
        "search_text": "fetched hotel",
        "row_data": {"travel_element": "Fetched Hotel", "supplier_currency": "NOK", "sales_currency": "NOK"},
    }
    rows = [{"row_id": "1", "travel_element": "Fetched Hotel", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1}]
    manager, browser, page = _browser_page(_payload(rows, library_rows=[library_row], revision="prefilled-focus"))
    try:
        page.locator('td[data-row-index="0"][data-key="travel_element"]').click()
        page.wait_for_timeout(250)
        assert page.locator('.suggestion-panel').count() == 0
        page.keyboard.press("ArrowRight")
        assert page.evaluate("document.activeElement.dataset.key") == "url"
    finally:
        browser.close()
        manager.stop()


def test_local_version_history_restores_an_earlier_calculator_state() -> None:
    rows = [
        {"row_id": "1", "travel_element": "Original service", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="version-history"))
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        cell.click()
        page.keyboard.press("Control+a")
        page.keyboard.type("Updated service")
        page.keyboard.press("Tab")

        versions = page.get_by_role("button", name=re.compile(r"Versions \(\d+\)"))
        assert int(re.search(r"\d+", versions.text_content()).group()) >= 2
        versions.click()
        version_items = page.locator('[data-version-id]')
        assert version_items.count() >= 2
        version_items.last.click()

        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Original service"
        assert page.locator('#calculator-sync-status').text_content().startswith("Recovered version from")
    finally:
        browser.close()
        manager.stop()


def test_cross_row_formula_dependents_refresh_immediately_after_edit() -> None:
    rows = [
        {"row_id": "1", "gross_price_per_unit": 100, "units": 2, "supplier_currency": "NOK", "sales_currency": "NOK"},
        {"row_id": "2", "gross_price_per_unit": "=S7/4", "units": 1, "supplier_currency": "NOK", "sales_currency": "NOK"},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="a1-dependent-refresh"))
    try:
        dependent = page.locator('td[data-row-index="1"][data-key="gross_price"]')
        assert dependent.text_content().strip() == "50.00"

        source = page.locator('td[data-row-index="0"][data-key="gross_price_per_unit"]')
        source.click()
        source.click()
        page.keyboard.press("Control+a")
        page.keyboard.type("200")
        page.keyboard.press("Tab")

        assert dependent.text_content().strip() == "100.00"
    finally:
        browser.close()
        manager.stop()
