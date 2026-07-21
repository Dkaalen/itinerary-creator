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
