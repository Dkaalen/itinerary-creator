from __future__ import annotations

import json

from support.calculator_browser_harness import (
    calculator_payload,
    open_blank_calculator_browser_page,
)


def _transport_payload(*, include_rows: bool) -> dict[str, object]:
    payload = calculator_payload(
        [{"row_id": "1", "supplier_currency": "NOK", "sales_currency": "EUR"}],
        revision="library-transport",
    )
    payload.update(
        {
            "library_payload_version": "compact-v2",
            "library_fingerprint": "compact-v2:ranking:test-workbook",
            "library_row_fields": ["travel_element", "type", "supplier"],
            "library_row_count": 1,
            "library_rows": [
                {
                    "i": "Transfers:10",
                    "w": "Transfers",
                    "x": 10,
                    "c": "Norway",
                    "g": "Transfer",
                    "v": {"0": "Norway in a Nutshell", "1": "Transfer", "2": "Fjord Tours"},
                }
            ] if include_rows else [],
        }
    )
    return payload


def test_browser_retains_rows_acknowledges_contract_and_reports_cache_loss() -> None:
    manager, browser, page = open_blank_calculator_browser_page()
    try:
        page.evaluate(
            """() => {
                window.__libraryTransport = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type !== 'streamlit:setComponentValue') return;
                    try {
                        const value = JSON.parse(event.data.value);
                        if (value.action === 'library_transport') window.__libraryTransport.push(value.library_transport);
                    } catch (_error) {}
                });
            }"""
        )
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            _transport_payload(include_rows=True),
        )
        page.wait_for_selector('td[data-key="travel_element"]')
        page.wait_for_function("window.__libraryTransport.length >= 1")

        assert page.evaluate("calculatorState.libraryRows.length") == 1
        assert page.evaluate("window.__libraryTransport.at(-1).status") == "retained"
        assert page.evaluate("window.sessionStorage.length") == 1

        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            _transport_payload(include_rows=False),
        )
        page.wait_for_function("window.__libraryTransport.length >= 2")
        assert page.evaluate("calculatorState.libraryRows.length") == 1
        assert page.evaluate("window.__libraryTransport.at(-1).status") == "retained"

        page.evaluate("window.sessionStorage.clear()")
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            _transport_payload(include_rows=False),
        )
        page.wait_for_function("window.__libraryTransport.at(-1).status === 'cache_miss'")
        # The live page can keep its in-memory index while Python responds to the
        # cache-miss signal with a full payload on the next rerun.
        assert page.evaluate("calculatorState.libraryRows.length") == 1

        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            _transport_payload(include_rows=True),
        )
        page.wait_for_function("window.__libraryTransport.at(-1).status === 'retained'")
        assert page.evaluate("calculatorState.libraryRows.length") == 1
        assert page.evaluate("window.sessionStorage.length") == 1
    finally:
        browser.close()
        manager.stop()
