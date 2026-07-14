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


def test_typing_pause_never_triggers_streamlit_sync_or_replaces_active_edit() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{"row_id": "1", "type": "", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK"}],
            revision="non-blocking-edit",
        )
    )
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(event.data.value);
                    }
                });
            }"""
        )
        cell = page.locator('td[data-row-index="0"][data-key="type"]')
        cell.click()
        page.keyboard.type("Ar")
        page.wait_for_timeout(800)
        page.keyboard.type("rival")
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(900)

        assert cell.text_content().strip() == "Arrival"
        assert page.evaluate("calculatorState.rows[0].type") == "Arrival"
        assert page.evaluate("document.activeElement.dataset.key") == "type"
        assert page.evaluate("activeCellEditing") is True
        assert page.evaluate("window.getSelection().anchorOffset") == len("Arrival") - 1
        assert page.evaluate("window.__calculatorComponentValues") == []
        assert page.locator("#calculator-sync-status").text_content() == "Unsaved changes"
    finally:
        browser.close()
        manager.stop()


def test_travel_element_autocomplete_stays_open_during_a_typing_pause() -> None:
    library_row = {
        "library_id": "oslo-hotel",
        "label": "Oslo Hotel",
        "preview": "Hotel in Oslo",
        "travel_element": "Oslo Hotel",
        "supplier": "Supplier",
        "country": "Norway",
        "category": "Hotel",
        "type": "Hotel",
        "comments": "",
        "search_text": "oslo hotel norway",
        "url": "",
        "row_data": {
            "row_id": "",
            "type": "Hotel",
            "travel_element": "Oslo Hotel",
            "supplier": "Supplier",
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
        },
    }
    manager, browser, page = _browser_page(
        _payload(
            [{"row_id": "1", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK"}],
            library_rows=[library_row],
            revision="autocomplete-no-sync",
        )
    )
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(event.data.value);
                    }
                });
            }"""
        )
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.type("Osl")
        page.wait_for_timeout(900)

        assert page.locator(".suggestion-item").count() == 1
        assert page.evaluate("document.activeElement.dataset.key") == "travel_element"
        assert page.evaluate("activeCellEditing") is True
        assert page.evaluate("window.__calculatorComponentValues") == []

        page.locator(".suggestion-item").click()
        assert cell.text_content().strip() == "Oslo Hotel"
    finally:
        browser.close()
        manager.stop()


def test_large_grid_text_typing_avoids_full_recalculation_and_per_key_draft_writes() -> None:
    rows = [
        {
            "row_id": str(index + 1),
            "travel_element": "",
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
            "gross_price_per_unit": 100,
            "units": 1,
        }
        for index in range(93)
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="large-grid-fast-text"))
    try:
        page.evaluate(
            """() => {
                window.__calculateRowsCalls = 0;
                window.__draftSaveCalls = 0;
                const originalCalculateRows = calculateRows;
                const originalSaveCalculatorDraft = saveCalculatorDraft;
                calculateRows = (...args) => {
                    window.__calculateRowsCalls += 1;
                    return originalCalculateRows(...args);
                };
                saveCalculatorDraft = (...args) => {
                    window.__draftSaveCalls += 1;
                    return originalSaveCalculatorDraft(...args);
                };
            }"""
        )
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.type("Oslo arrival hotel")
        page.wait_for_timeout(550)

        assert cell.text_content().strip() == "Oslo arrival hotel"
        assert page.evaluate("window.__calculateRowsCalls") == 0
        assert page.evaluate("window.__draftSaveCalls") == 1
    finally:
        browser.close()
        manager.stop()


def test_explicit_download_submits_the_latest_unsynced_browser_state() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{"row_id": "1", "type": "", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK"}],
            revision="explicit-submit",
        )
    )
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(JSON.parse(event.data.value));
                    }
                });
            }"""
        )
        cell = page.locator('td[data-row-index="0"][data-key="type"]')
        cell.click()
        page.keyboard.type("Arrival")
        page.get_by_role("button", name="Download Excel").click()

        values = page.evaluate("window.__calculatorComponentValues")
        assert len(values) == 1
        assert values[0]["action"] == "download"
        assert values[0]["rows"][0]["type"] == "Arrival"
    finally:
        browser.close()
        manager.stop()


def test_currency_rate_rerender_keeps_the_unsynced_browser_draft() -> None:
    initial_payload = _payload(
        [{"row_id": "1", "travel_element": "", "supplier_currency": "EUR", "sales_currency": "NOK"}],
        revision="stable-editable-state",
    )
    manager, browser, page = _browser_page(initial_payload)
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.type("Oslo arrival")
        page.wait_for_timeout(500)

        changed_rates_payload = {
            **initial_payload,
            "rows": [{"row_id": "1", "travel_element": "", "supplier_currency": "EUR", "sales_currency": "NOK"}],
            "currency_rates": {"NOK": 1, "EUR": 14},
        }
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            changed_rates_payload,
        )
        page.wait_for_selector('td[data-row-index="0"][data-key="travel_element"]')

        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Oslo arrival"
        assert page.evaluate("calculatorState.rows[0].travel_element") == "Oslo arrival"
        assert page.evaluate("calculatorState.currencyRates.EUR") == 14
        assert page.locator("#calculator-sync-status").text_content() == "Unsaved changes"
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
        page.evaluate("flushRecoverySnapshot()")
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


def test_selected_day_cell_stays_compact_and_never_highlights_text() -> None:
    manager, browser, page = _browser_page(
        _payload([{"row_id": "1", "day": "Day 1", "supplier_currency": "NOK", "sales_currency": "NOK"}], revision="clean-selection")
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="day"]')
        cell.click()

        assert page.evaluate("activeCellEditing") is False
        assert page.evaluate("window.getSelection().toString()") == ""
        assert page.evaluate("getComputedStyle(document.activeElement).overflow") == "hidden"
        assert "editing-cell" not in (cell.get_attribute("class") or "")

        page.keyboard.type("Day 2")
        assert cell.text_content().strip() == "Day 2"
        assert page.evaluate("window.getSelection().toString()") == ""
    finally:
        browser.close()
        manager.stop()


def test_formula_bar_and_selected_grid_cell_stay_in_sync() -> None:
    manager, browser, page = _browser_page(
        _payload([{"row_id": "3", "travel_element": "Original hotel", "supplier_currency": "NOK", "sales_currency": "NOK"}], revision="formula-grid-sync")
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        formula_bar = page.get_by_label("Active cell value")
        formula_bar.fill("Oslo: Hotel Dennis - Breakfast included")

        assert cell.text_content().strip() == "Oslo: Hotel Dennis - Breakfast included"
        assert page.evaluate("calculatorState.rows[0].travel_element") == "Oslo: Hotel Dennis - Breakfast included"
        assert page.locator(".formula-reference").text_content() == "Travel element · row 3"
    finally:
        browser.close()
        manager.stop()


def test_sales_price_expression_is_precise_internally_and_shows_two_decimals() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{
                "row_id": "1",
                "gross_price_per_unit": 600,
                "units": 1,
                "supplier_commission": 0,
                "supplier_currency": "NOK",
                "sales_price_per_unit": 600,
                "sales_currency": "NOK",
            }],
            revision="sales-price-expression",
        )
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="sales_price_per_unit"]')
        cell.click()
        page.keyboard.type("600/0.7")
        page.keyboard.press("Tab")

        assert cell.text_content().strip() == "857.14"
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(600 / 0.7)
        assert page.evaluate("calculatorState.rows[0].price") == pytest.approx(857.14)
    finally:
        browser.close()
        manager.stop()


def test_sales_margin_shortcuts_apply_10_15_20_percent_and_reset_to_gross() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{
                "row_id": "1",
                "gross_price_per_unit": 600,
                "units": 1,
                "supplier_commission": 0,
                "supplier_currency": "NOK",
                "sales_price_per_unit": 600,
                "sales_currency": "NOK",
            }],
            revision="sales-margin-shortcuts",
        )
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="sales_price_per_unit"]')
        cell.click()
        tools = page.locator("#sales-price-tools")
        assert tools.is_visible()

        tools.get_by_role("button", name="20%").click()
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(750)
        assert cell.text_content().strip() == "750.00"

        page.locator("#sales-price-tools").get_by_role("button", name="15%").click()
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(600 / 0.85)
        assert cell.text_content().strip() == "705.88"

        page.locator("#sales-price-tools").get_by_role("button", name="10%").click()
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(600 / 0.9)
        assert cell.text_content().strip() == "666.67"

        page.locator("#sales-price-tools").get_by_role("button", name="Use gross").click()
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(600)
        assert cell.text_content().strip() == "600.00"
    finally:
        browser.close()
        manager.stop()


def test_prepared_excel_downloads_from_the_grid_toolbar() -> None:
    import base64

    payload = _payload(
        [{"row_id": "1", "travel_element": "Hotel", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="prepared-excel",
    )
    payload["pending_download"] = {
        "filename": "Oslo Trip.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content_base64": base64.b64encode(b"xlsx-test-content").decode("ascii"),
    }
    manager, browser, page = _browser_page(payload)
    try:
        with page.expect_download() as download_info:
            page.get_by_role("button", name="Download Excel").click()
        download = download_info.value

        assert download.suggested_filename == "Oslo Trip.xlsx"
        assert page.locator("#calculator-sync-status").text_content() == "Excel downloaded"
    finally:
        browser.close()
        manager.stop()


def test_editing_after_excel_is_prepared_invalidates_the_stale_browser_download() -> None:
    import base64

    payload = _payload(
        [{"row_id": "1", "type": "Hotel", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="invalidate-prepared-excel",
    )
    payload["pending_download"] = {
        "filename": "Old.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content_base64": base64.b64encode(b"old").decode("ascii"),
    }
    manager, browser, page = _browser_page(payload)
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(JSON.parse(event.data.value));
                    }
                });
            }"""
        )
        cell = page.locator('td[data-row-index="0"][data-key="type"]')
        cell.click()
        page.keyboard.type("Transfer")

        assert page.evaluate("calculatorState.pendingDownload") is None
        assert page.locator("#calculator-excel-ready-status").count() == 0

        page.get_by_role("button", name="Download Excel").click()
        values = page.evaluate("window.__calculatorComponentValues")
        assert len(values) == 1
        assert values[0]["action"] == "download"
        assert values[0]["rows"][0]["type"] == "Transfer"
    finally:
        browser.close()
        manager.stop()


def test_same_revision_backend_rerender_cannot_restore_a_stale_excel_download() -> None:
    import base64

    payload = _payload(
        [{"row_id": "1", "type": "Hotel", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="stale-download-rerender",
    )
    payload["pending_download"] = {
        "filename": "Old.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content_base64": base64.b64encode(b"old").decode("ascii"),
    }
    manager, browser, page = _browser_page(payload)
    try:
        cell = page.locator('td[data-row-index="0"][data-key="type"]')
        cell.click()
        page.keyboard.type("Transfer")
        assert page.evaluate("calculatorState.pendingDownload") is None

        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            payload,
        )

        assert page.evaluate("calculatorState.rows[0].type") == "Transfer"
        assert page.evaluate("calculatorState.pendingDownload") is None
        assert page.locator("#calculator-excel-ready-status").count() == 0
    finally:
        browser.close()
        manager.stop()
