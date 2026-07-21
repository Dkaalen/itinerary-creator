from __future__ import annotations

import re

import pytest

from support.calculator_browser_harness import (
    calculator_payload as _payload,
    open_calculator_browser_page as _browser_page,
)


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
