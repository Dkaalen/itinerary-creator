from __future__ import annotations

import re

import pytest

from support.calculator_browser_harness import (
    calculator_payload as _payload,
    open_blank_calculator_browser_page as _blank_browser_page,
    open_calculator_browser_page as _browser_page,
)


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

def test_component_bridge_does_not_send_session_messages_before_first_render() -> None:
    manager, browser, page = _blank_browser_page()
    try:
        page.evaluate(
            """() => {
                window.__bridgeMessages = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.isStreamlitMessage) window.__bridgeMessages.push(event.data.type);
                });
                Streamlit.setFrameHeight(321);
                Streamlit.setComponentValue('too-early');
            }"""
        )
        page.wait_for_timeout(50)
        assert page.evaluate("window.__bridgeMessages") == []

        payload = _payload(
            [{"row_id": "1", "supplier_currency": "NOK", "sales_currency": "EUR"}],
            revision="bridge-render-gate",
        )
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            payload,
        )
        page.wait_for_selector('td[data-key="travel_element"]')
        page.wait_for_timeout(50)

        messages = page.evaluate("window.__bridgeMessages")
        assert "streamlit:setFrameHeight" in messages
        assert "streamlit:setComponentValue" not in messages
    finally:
        browser.close()
        manager.stop()

def test_open_project_requires_confirmation_before_replacing_current_work() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{"row_id": "1", "travel_element": "Existing hotel", "supplier_currency": "NOK", "sales_currency": "EUR"}],
            revision="open-project-confirmation",
        )
    )
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.confirm = () => false;
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(JSON.parse(event.data.value));
                    }
                });
            }"""
        )
        page.locator('[data-action="excel-file-input"]').set_input_files(
            {
                "name": "Replacement.xlsx",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "buffer": b"PK\x03\x04replacement",
            }
        )
        page.wait_for_timeout(150)

        assert page.evaluate("window.__calculatorComponentValues") == []
        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Existing hotel"
    finally:
        browser.close()
        manager.stop()

def test_backend_ack_clears_dirty_state_only_after_matching_request_is_accepted() -> None:
    initial = _payload(
        [{"row_id": "1", "type": "", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="ack-initial",
    )
    manager, browser, page = _browser_page(initial)
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
        page.wait_for_function("window.__calculatorComponentValues.length === 1")

        submitted = page.evaluate("window.__calculatorComponentValues[0]")
        assert submitted["request_id"]
        assert page.evaluate("calculatorState.dirty") is True
        assert page.evaluate("pendingCalculatorRequest.requestId") == submitted["request_id"]

        accepted = _payload(submitted["rows"], revision="ack-server")
        accepted["draft_storage_key"] = initial["draft_storage_key"]
        accepted["component_ack"] = {
            "request_id": submitted["request_id"],
            "action": "download",
            "status": "accepted",
            "message": "",
            "server_state_revision": "ack-server",
        }
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            accepted,
        )
        page.wait_for_function("pendingCalculatorRequest === null")

        assert page.evaluate("calculatorState.dirty") is False
        assert page.evaluate("activeBackendRevision") == "ack-server"
        assert page.locator("#calculator-sync-status").text_content() == "Saved"
    finally:
        browser.close()
        manager.stop()

def test_rejected_stale_request_loads_new_backend_state_and_keeps_old_draft_recoverable() -> None:
    initial = _payload(
        [{"row_id": "1", "type": "Arrival", "travel_element": "Old backend", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="stale-initial",
    )
    manager, browser, page = _browser_page(initial)
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
        page.evaluate("calculatorState.rows[0].travel_element = 'Unsaved browser edit'; markLocalDraft(); rerender();")
        page.get_by_role("button", name="Download Excel").click()
        page.wait_for_function("window.__calculatorComponentValues.length === 1")
        submitted = page.evaluate("window.__calculatorComponentValues[0]")

        rejected = _payload(
            [{"row_id": "1", "type": "Arrival", "travel_element": "New backend", "supplier_currency": "NOK", "sales_currency": "NOK"}],
            revision="stale-server",
        )
        rejected["draft_storage_key"] = initial["draft_storage_key"]
        rejected["component_ack"] = {
            "request_id": submitted["request_id"],
            "action": "download",
            "status": "rejected_stale",
            "message": "The older action was not applied.",
            "server_state_revision": "stale-server",
        }
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            rejected,
        )
        page.wait_for_function("pendingCalculatorRequest === null")

        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "New backend"
        assert "not applied" in page.locator("#calculator-sync-status").text_content()
        stored = page.evaluate("key => JSON.parse(window.localStorage.getItem(key))", initial["draft_storage_key"])
        assert stored["rows"][0]["travel_element"] == "Unsaved browser edit"
    finally:
        browser.close()
        manager.stop()

def test_edits_made_after_submit_are_rebased_on_the_accepted_backend_revision() -> None:
    initial = _payload(
        [{"row_id": "1", "type": "Arrival", "travel_element": "Submitted value", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="rebase-initial",
    )
    manager, browser, page = _browser_page(initial)
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
        page.get_by_role("button", name="Download Excel").click()
        page.wait_for_function("window.__calculatorComponentValues.length === 1")
        submitted = page.evaluate("window.__calculatorComponentValues[0]")

        page.evaluate("calculatorState.rows[0].travel_element = 'Edited after submit'; markLocalDraft(); rerender();")
        accepted = _payload(submitted["rows"], revision="rebase-server")
        accepted["draft_storage_key"] = initial["draft_storage_key"]
        accepted["component_ack"] = {
            "request_id": submitted["request_id"],
            "action": "download",
            "status": "accepted",
            "message": "",
            "server_state_revision": "rebase-server",
        }
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            accepted,
        )
        page.wait_for_function("pendingCalculatorRequest === null")

        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Edited after submit"
        assert page.evaluate("calculatorState.dirty") is True
        assert page.evaluate("activeBackendRevision") == "rebase-server"
        assert page.locator("#calculator-sync-status").text_content() == "Unsaved changes"
    finally:
        browser.close()
        manager.stop()

def test_back_navigation_submits_invalid_financial_draft_without_blocking() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{
                "row_id": "1",
                "day": "Day 1",
                "type": "Hotel",
                "travel_element": "Oslo hotel",
                "gross_price_per_unit": "=10/0",
                "supplier_currency": "XYZ",
                "sales_currency": "NOK",
            }],
            revision="draft-safe-back",
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
        page.get_by_role("button", name="Back").click()
        page.wait_for_function("window.__calculatorComponentValues.length === 1")

        submitted = page.evaluate("window.__calculatorComponentValues[0]")
        assert submitted["action"] == "close"
        assert submitted["client_has_validation_errors"] is True
        assert submitted["rows"][0]["gross_price_per_unit"] == "=10/0"
    finally:
        browser.close()
        manager.stop()

def test_generation_blocks_only_missing_itinerary_fields_with_row_feedback() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{
                "row_id": "12",
                "day": "Day 1",
                "type": "Hotel",
                "travel_element": "",
                "supplier_currency": "NOK",
                "sales_currency": "NOK",
            }],
            revision="generation-fields",
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
        page.get_by_role("button", name="Agent itinerary").click()
        page.wait_for_timeout(100)

        assert page.evaluate("window.__calculatorComponentValues") == []
        assert "Row 12" in page.locator(".calculator-validation-panel").text_content()
        assert "Travel element" in page.locator(".calculator-validation-panel").text_content()
        assert page.locator("#calculator-sync-status").text_content() == "Complete the highlighted itinerary fields"
    finally:
        browser.close()
        manager.stop()

def test_generation_allows_financial_errors_when_itinerary_fields_are_complete() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{
                "row_id": "3",
                "day": "Day 1",
                "type": "Hotel",
                "travel_element": "Oslo hotel",
                "gross_price_per_unit": "=10/0",
                "supplier_currency": "XYZ",
                "sales_currency": "NOK",
            }],
            revision="generation-finance-independent",
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
        page.get_by_role("button", name="Agent itinerary").click()
        page.wait_for_function("window.__calculatorComponentValues.length === 1")

        submitted = page.evaluate("window.__calculatorComponentValues[0]")
        assert submitted["action"] == "generate_agent"
        assert submitted["client_has_validation_errors"] is True
        assert submitted["rows"][0]["gross_price_per_unit"] == "=10/0"
    finally:
        browser.close()
        manager.stop()

def test_transient_ack_keeps_invalid_browser_draft_on_same_backend_revision() -> None:
    initial = _payload(
        [{
            "row_id": "1",
            "day": "Day 1",
            "type": "Hotel",
            "travel_element": "Oslo hotel",
            "gross_price_per_unit": 100,
            "units": 1,
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
        }],
        revision="transient-draft-base",
    )
    manager, browser, page = _browser_page(initial)
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
        cell = page.locator('td[data-row-index="0"][data-key="gross_price_per_unit"]')
        cell.click()
        cell.click()
        page.keyboard.press("Control+a")
        page.keyboard.type("=10/0")
        page.keyboard.press("Tab")
        page.get_by_role("button", name="Agent itinerary").click()
        page.wait_for_function("window.__calculatorComponentValues.length === 1")

        submitted = page.evaluate("window.__calculatorComponentValues[0]")
        assert submitted["client_has_validation_errors"] is True

        transient = dict(initial)
        transient["component_ack"] = {
            "request_id": submitted["request_id"],
            "action": "generate_agent",
            "status": "accepted_transient",
            "message": "Draft kept in the browser until its highlighted values are resolved.",
            "server_state_revision": initial["state_revision"],
        }
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            transient,
        )
        page.wait_for_function("pendingCalculatorRequest === null")

        assert page.evaluate("calculatorState.rows[0].gross_price_per_unit") == "=10/0"
        assert page.evaluate("calculatorState.dirty") is True
        assert page.locator('td[data-row-index="0"][data-key="gross_price"]').text_content().strip() == "#DIV/0!"
    finally:
        browser.close()
        manager.stop()
