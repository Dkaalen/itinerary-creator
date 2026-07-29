from __future__ import annotations

import re

import pytest

from support.calculator_browser_harness import (
    calculator_payload as _payload,
    open_calculator_browser_page as _browser_page,
)


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
        page.get_by_text("More tools", exact=True).click()
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

def test_single_cell_copy_and_paste_work_in_grid_selection_mode() -> None:
    rows = [
        {"row_id": "1", "travel_element": "Oslo hotel", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "2", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "3", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="single-cell-clipboard"))
    try:
        source = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        target = page.locator('td[data-row-index="1"][data-key="travel_element"]')
        source.click()
        copied = page.evaluate(
            """() => {
                const data = new DataTransfer();
                document.dispatchEvent(new ClipboardEvent('copy', {clipboardData: data, bubbles: true}));
                return data.getData('text/plain');
            }"""
        )
        target.click()
        page.evaluate(
            """text => {
                const data = new DataTransfer();
                data.setData('text/plain', text);
                document.dispatchEvent(new ClipboardEvent('paste', {clipboardData: data, bubbles: true}));
            }""",
            copied,
        )

        assert copied == "Oslo hotel"
        assert target.text_content().strip() == "Oslo hotel"
        assert page.evaluate("calculatorState.rows[1].travel_element") == "Oslo hotel"

        blank = page.locator('td[data-row-index="2"][data-key="travel_element"]')
        blank.click()
        blank_text = page.evaluate(
            """() => {
                const data = new DataTransfer();
                document.dispatchEvent(new ClipboardEvent('copy', {clipboardData: data, bubbles: true}));
                return data.getData('text/plain');
            }"""
        )
        source.click()
        page.evaluate(
            """text => {
                const data = new DataTransfer();
                data.setData('text/plain', text);
                document.dispatchEvent(new ClipboardEvent('paste', {clipboardData: data, bubbles: true}));
            }""",
            blank_text,
        )
        assert source.text_content().strip() == ""
    finally:
        browser.close()
        manager.stop()

def test_paste_while_editing_inserts_plain_text_at_the_caret() -> None:
    rows = [{"row_id": "1", "travel_element": "Oslo hotel", "supplier_currency": "NOK", "sales_currency": "EUR"}]
    manager, browser, page = _browser_page(_payload(rows, revision="editing-cell-clipboard"))
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        cell.click()
        page.keyboard.press("End")
        page.evaluate(
            """() => {
                const data = new DataTransfer();
                data.setData('text/plain', ' arrival');
                document.activeElement.dispatchEvent(new ClipboardEvent('paste', {clipboardData: data, bubbles: true}));
            }"""
        )

        assert cell.text_content().strip() == "Oslo hotel arrival"
        assert page.evaluate("calculatorState.rows[0].travel_element") == "Oslo hotel arrival"
        assert page.evaluate("activeCellEditing") is True
    finally:
        browser.close()
        manager.stop()


def test_single_copied_value_broadcasts_to_shift_selected_rows_and_undoes_once() -> None:
    rows = [
        {"row_id": "1", "day": "Day 1", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "2", "day": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "3", "day": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="broadcast-selected-range"))
    try:
        source = page.locator('td[data-row-index="0"][data-key="day"]')
        source.click()
        page.keyboard.press("Control+c")
        page.keyboard.press("Shift+ArrowDown")
        page.keyboard.press("Shift+ArrowDown")
        page.keyboard.press("Control+v")

        assert page.locator('td[data-key="day"]').all_text_contents() == ["Day 1", "Day 1", "Day 1"]
        assert page.evaluate("normalizedSelection()") == {"top": 0, "bottom": 2, "left": 1, "right": 1}

        page.keyboard.press("Control+z")
        assert page.locator('td[data-key="day"]').all_text_contents() == ["Day 1", "", ""]
    finally:
        browser.close()
        manager.stop()


def test_copied_rectangle_repeats_across_a_compatible_selected_rectangle() -> None:
    rows = [
        {"row_id": "1", "day": "Day 1", "type": "Arrival", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "2", "day": "Day 2", "type": "Hotel", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "3", "day": "", "type": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "4", "day": "", "type": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "5", "day": "", "type": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "6", "day": "", "type": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="repeat-copied-rectangle"))
    try:
        page.locator('td[data-row-index="0"][data-key="day"]').click()
        page.locator('td[data-row-index="1"][data-key="type"]').click(modifiers=["Shift"])
        page.evaluate(
            """() => {
                window.__calculatorClipboard = new DataTransfer();
                document.dispatchEvent(new ClipboardEvent('copy', {
                    clipboardData: window.__calculatorClipboard,
                    bubbles: true
                }));
            }"""
        )

        page.locator('td[data-row-index="2"][data-key="day"]').click()
        page.locator('td[data-row-index="5"][data-key="type"]').click(modifiers=["Shift"])
        page.evaluate(
            """() => document.dispatchEvent(new ClipboardEvent('paste', {
                clipboardData: window.__calculatorClipboard,
                bubbles: true
            }))"""
        )

        assert page.evaluate(
            "calculatorState.rows.slice(2, 6).map(row => [row.day, row.type])"
        ) == [
            ["Day 1", "Arrival"],
            ["Day 2", "Hotel"],
            ["Day 1", "Arrival"],
            ["Day 2", "Hotel"],
        ]
    finally:
        browser.close()
        manager.stop()


def test_fill_shortcuts_distinguish_repeated_values_from_numbered_sequences() -> None:
    rows = [
        {"row_id": "1", "day": "Day 1", "from_date": "01.01.2026", "gross_price_per_unit": "=R7*100", "units": 1, "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "2", "day": "", "gross_price_per_unit": "", "units": 2, "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "3", "day": "", "gross_price_per_unit": "", "units": 3, "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "4", "day": "", "gross_price_per_unit": "", "units": 4, "supplier_currency": "NOK", "sales_currency": "EUR"},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="fill-shortcuts"))
    try:
        day = page.locator('td[data-row-index="0"][data-key="day"]')
        day.click()
        for _ in range(3):
            page.keyboard.press("Shift+ArrowDown")
        page.keyboard.press("Control+Shift+d")
        assert page.evaluate("calculatorState.rows.map(row => row.day)") == ["Day 1", "Day 2", "Day 3", "Day 4"]
        assert page.evaluate("calculatorState.rows.map(row => row.from_date)") == ["01.01.2026", "02.01.2026", "03.01.2026", "04.01.2026"]

        page.keyboard.press("Control+z")
        day.click()
        for _ in range(3):
            page.keyboard.press("Shift+ArrowDown")
        page.get_by_text("More tools", exact=True).click()
        page.get_by_role("button", name="Fill sequence").click()
        assert page.evaluate("calculatorState.rows.map(row => row.day)") == ["Day 1", "Day 2", "Day 3", "Day 4"]

        page.keyboard.press("Control+z")
        day.click()
        for _ in range(3):
            page.keyboard.press("Shift+ArrowDown")
        page.keyboard.press("Control+d")
        assert page.evaluate("calculatorState.rows.map(row => row.day)") == ["Day 1", "Day 1", "Day 1", "Day 1"]

        formula = page.locator('td[data-row-index="0"][data-key="gross_price_per_unit"]')
        formula.click()
        page.keyboard.press("Shift+ArrowDown")
        page.keyboard.press("Control+d")
        assert page.evaluate("calculatorState.rows[1].gross_price_per_unit") == "=R8*100"
    finally:
        browser.close()
        manager.stop()


def test_fill_handle_continues_a_day_number_sequence() -> None:
    rows = [
        {"row_id": "1", "day": "Day 1", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "2", "day": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "3", "day": "", "supplier_currency": "NOK", "sales_currency": "EUR"},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="drag-day-series"))
    try:
        source = page.locator('td[data-row-index="0"][data-key="day"]')
        target = page.locator('td[data-row-index="2"][data-key="day"]')
        source.click()
        handle = source.locator('.fill-handle')
        handle.wait_for()
        handle_box = handle.bounding_box()
        target_box = target.bounding_box()
        page.mouse.move(handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
        page.mouse.down()
        page.mouse.move(target_box["x"] + target_box["width"] / 2, target_box["y"] + target_box["height"] / 2, steps=6)
        page.mouse.up()

        assert page.evaluate("calculatorState.rows.map(row => row.day)") == ["Day 1", "Day 2", "Day 3"]
        page.keyboard.press("Control+z")
        assert page.evaluate("calculatorState.rows.map(row => row.day)") == ["Day 1", "", ""]
    finally:
        browser.close()
        manager.stop()


def test_internal_formula_copy_translates_even_when_browser_keeps_only_plain_text() -> None:
    rows = [
        {"row_id": "1", "gross_price_per_unit": "=R7*100", "units": 1, "supplier_currency": "NOK", "sales_currency": "EUR"},
        {"row_id": "2", "gross_price_per_unit": "", "units": 2, "supplier_currency": "NOK", "sales_currency": "EUR"},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="plain-text-formula-copy"))
    try:
        source = page.locator('td[data-row-index="0"][data-key="gross_price_per_unit"]')
        target = page.locator('td[data-row-index="1"][data-key="gross_price_per_unit"]')
        source.click()
        copied_text = page.evaluate(
            """() => {
                const copied = new DataTransfer();
                document.dispatchEvent(new ClipboardEvent('copy', {clipboardData: copied, bubbles: true}));
                return copied.getData('text/plain');
            }"""
        )
        target.click()
        page.evaluate(
            """text => {
                const plainOnly = new DataTransfer();
                plainOnly.setData('text/plain', text);
                document.dispatchEvent(new ClipboardEvent('paste', {clipboardData: plainOnly, bubbles: true}));
            }""",
            copied_text,
        )

        assert page.evaluate("calculatorState.rows[1].gross_price_per_unit") == "=R8*100"
    finally:
        browser.close()
        manager.stop()


def test_large_range_paste_recalculates_and_records_history_once() -> None:
    rows = [
        {
            "row_id": str(index + 1),
            "day": "Day 1" if index == 0 else "",
            "supplier_currency": "NOK",
            "sales_currency": "EUR",
        }
        for index in range(93)
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="large-range-paste"))
    try:
        page.locator('td[data-row-index="0"][data-key="day"]').click()
        page.evaluate(
            """() => {
                window.__calculatorClipboard = new DataTransfer();
                document.dispatchEvent(new ClipboardEvent('copy', {
                    clipboardData: window.__calculatorClipboard,
                    bubbles: true
                }));
                window.__calculateRowsCalls = 0;
                window.__autofillDatesCalls = 0;
                window.__renderShellCalls = 0;
                const originalCalculateRows = calculateRows;
                const originalAutofillDates = autofillDatesFromArrival;
                const originalRenderShell = renderShell;
                calculateRows = (...args) => {
                    window.__calculateRowsCalls += 1;
                    return originalCalculateRows(...args);
                };
                autofillDatesFromArrival = (...args) => {
                    window.__autofillDatesCalls += 1;
                    return originalAutofillDates(...args);
                };
                renderShell = (...args) => {
                    window.__renderShellCalls += 1;
                    return originalRenderShell(...args);
                };
                calculatorState.selection = {startRow: 0, endRow: 92, startCol: 1, endCol: 1};
                activeCell = {rowIndex: 92, key: 'day'};
                calculatorState.selectedRowIndex = 92;
            }"""
        )
        page.evaluate(
            """() => document.dispatchEvent(new ClipboardEvent('paste', {
                clipboardData: window.__calculatorClipboard,
                bubbles: true
            }))"""
        )

        assert page.evaluate("window.__calculateRowsCalls") == 1
        assert page.evaluate("window.__autofillDatesCalls") == 1
        assert page.evaluate("window.__renderShellCalls") == 1
        assert page.evaluate("calculatorState.undoStack.length") == 1
        assert page.evaluate("calculatorState.rows.every(row => row.day === 'Day 1')") is True

        page.evaluate("window.__calculateRowsCalls = 0; window.__renderShellCalls = 0")
        page.keyboard.press("Control+z")
        assert page.evaluate("window.__calculateRowsCalls") == 1
        assert page.evaluate("window.__renderShellCalls") == 1
        assert page.evaluate("calculatorState.rows[0].day === 'Day 1' && calculatorState.rows.slice(1).every(row => row.day === '')") is True
    finally:
        browser.close()
        manager.stop()
