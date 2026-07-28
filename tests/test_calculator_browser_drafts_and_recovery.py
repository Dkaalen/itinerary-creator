from __future__ import annotations

import re

import pytest

from support.calculator_browser_harness import (
    install_storage_quota as _install_storage_quota,
    open_recovery_browser_page as _recovery_browser_page,
    recovery_payload as _recovery_payload,
    calculator_payload as _payload,
    open_calculator_browser_page as _browser_page,
)


def _recovery_page(*, revision: str = "recovery-test"):
    return _recovery_browser_page(revision=revision)


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

def test_invalid_navigation_draft_restores_after_calculator_remount() -> None:
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
        revision="draft-safe-remount",
    )
    manager, browser, page = _browser_page(initial)
    try:
        cell = page.locator('td[data-row-index="0"][data-key="gross_price_per_unit"]')
        cell.click()
        cell.click()
        page.keyboard.press("Control+a")
        page.keyboard.type("=10/0")
        page.keyboard.press("Tab")
        page.get_by_role("button", name="Back").click()
        page.wait_for_function("pendingCalculatorRequest !== null")

        page.evaluate(
            """payload => {
                flushLocalDraftSave();
                pendingCalculatorRequest = null;
                calculatorState = null;
                activeCell = null;
                activeBackendRevision = null;
                activeDraftStorageKey = null;
                hasLocalDraft = false;
                initializeState(payload);
                rerender();
            }""",
            initial,
        )

        assert page.evaluate("calculatorState.rows[0].gross_price_per_unit") == "=10/0"
        assert page.evaluate("calculatorState.dirty") is True
        assert page.locator("#calculator-sync-status").text_content() == "Local changes restored"
    finally:
        browser.close()
        manager.stop()

def test_recovery_storage_uses_compact_hashes_and_row_deltas() -> None:
    manager, browser, page, payload = _recovery_page(revision="compact-delta")
    try:
        page.evaluate(
            """() => {
              calculatorState.rows = Array.from({length: 10}, (_, index) => ({
                row_id: String(index + 1),
                travel_element: `Original service ${index}`,
                comments: 'baseline '.repeat(20),
                gross_price_per_unit: 100,
                units: 1,
                supplier_currency: 'NOK',
                sales_currency: 'NOK'
              }));
              window.ItineraryCalculator.storage.saveRecoverySnapshot(calculatorState, activeBackendRevision, 'expanded');
              calculatorState.rows[0].travel_element = 'Updated service';
              markLocalDraft(false);
              flushRecoverySnapshot('edited');
            }"""
        )
        stored = page.evaluate(
            "key => JSON.parse(window.localStorage.getItem(`${key}.versions`))",
            payload["draft_storage_key"],
        )

        assert stored["schemaVersion"] == 4
        assert stored["entries"][0]["kind"] == "full"
        assert len(stored["entries"][0]["hash"]) == 16
        assert "signature" not in stored["entries"][0]
        assert stored["entries"][1]["kind"] == "delta"
        assert "rows" not in stored["entries"][1]
        assert stored["entries"][1]["rowChanges"]

        snapshots = page.evaluate("window.ItineraryCalculator.storage.loadRecoverySnapshots()")
        assert snapshots[0]["rows"][0]["travel_element"] == "Updated service"
        assert snapshots[1]["rows"][0]["travel_element"] == "Original service 0"
        legacy_size = page.evaluate(
            """snapshots => JSON.stringify(snapshots.map((snapshot) => ({
              ...snapshot,
              signature: JSON.stringify({
                rows: snapshot.rows,
                numberOfPax: snapshot.numberOfPax ?? null,
                showAdvanced: Boolean(snapshot.showAdvanced),
                columnWidths: {...(snapshot.columnWidths || {})}
              })
            }))).length""",
            snapshots,
        )
        compact_size = page.evaluate("window.localStorage.getItem(window.ItineraryCalculator.storage.recoveryStorageKey()).length")
        assert compact_size < legacy_size

        page.get_by_role("button", name=re.compile(r"Versions \(\d+\)")).click()
        assert "stored in this browser" in page.locator(".calculator-version-heading").text_content()
    finally:
        browser.close()
        manager.stop()

def test_large_projects_adapt_retention_and_preserve_long_values() -> None:
    manager, browser, page, _payload_data = _recovery_page(revision="large-recovery")
    try:
        rows = [
            {
                "row_id": str(index + 1),
                "travel_element": f"Service {index}",
                "comments": (f"Long comment {index} " + "x" * 8000),
                "url": "https://example.com/" + ("path/" * 160) + str(index),
                "gross_price_per_unit": "=100/10*0.8",
                "units": 1,
                "supplier_currency": "NOK",
                "sales_currency": "NOK",
            }
            for index in range(93)
        ]
        page.evaluate(
            """rows => {
              calculatorState.rows = rows;
              for (let index = 0; index < 7; index += 1) {
                calculatorState.rows[0].comments = `${rows[0].comments}-${index}`;
                window.ItineraryCalculator.storage.saveRecoverySnapshot(calculatorState, activeBackendRevision, `large-${index}`);
              }
              calculatorState.recoverySnapshots = window.ItineraryCalculator.storage.loadRecoverySnapshots();
            }""",
            rows,
        )

        snapshots = page.evaluate("window.ItineraryCalculator.storage.loadRecoverySnapshots()")
        assert 1 <= len(snapshots) <= 4
        assert snapshots[0]["rows"][92]["gross_price_per_unit"] == "=100/10*0.8"
        assert snapshots[0]["rows"][92]["url"].endswith("92")
        assert snapshots[0]["rows"][92]["comments"].startswith("Long comment 92")
        assert page.evaluate("window.ItineraryCalculator.storage.storageUsage().totalBytes") > 500_000
    finally:
        browser.close()
        manager.stop()

def test_quota_prunes_old_versions_before_current_draft() -> None:
    manager, browser, page, payload = _recovery_page(revision="quota-prune")
    try:
        page.evaluate(
            """() => {
              calculatorState.rows[0].travel_element = 'Version two';
              window.ItineraryCalculator.storage.saveRecoverySnapshot(calculatorState, activeBackendRevision, 'second');
            }"""
        )
        _install_storage_quota(page, 17_500)
        long_comment = "current-draft-" + "z" * 8000
        saved = page.evaluate(
            """comment => {
              calculatorState.rows[0].comments = comment;
              return window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
            }""",
            long_comment,
        )

        assert saved is True
        draft = page.evaluate(
            "key => JSON.parse(window.localStorage.getItem(key))",
            payload["draft_storage_key"],
        )
        assert draft["rows"][0]["comments"] == long_comment
        assert page.evaluate("window.localStorage.getItem(window.ItineraryCalculator.storage.recoveryStorageKey())") is None
        assert page.evaluate("calculatorState.recoverySnapshots.length") == 0
        assert page.get_by_role("button", name="Versions (0)").count() == 1
        status = page.locator("#calculator-recovery-status")
        assert status.text_content() == "Local recovery reduced"
        status.click()
        assert "current Calculator draft" in page.locator(".calculator-local-recovery-info").text_content()
        assert page.locator("#calculator-recovery-warning").count() == 0
    finally:
        browser.close()
        manager.stop()

def test_unavailable_storage_shows_one_quiet_status() -> None:
    manager, browser, page, _payload_data = _recovery_page(revision="quota-warning")
    try:
        _install_storage_quota(page, 2_000)
        saved = page.evaluate(
            """() => {
              calculatorState.rows[0].comments = 'q'.repeat(12000);
              return window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
            }"""
        )

        assert saved is False
        status = page.locator("#calculator-recovery-status")
        assert status.count() == 1
        assert status.text_content() == "Local recovery unavailable"
        assert "danger" not in (status.get_attribute("class") or "")
        status.click()
        details = page.locator(".calculator-local-recovery-info").text_content()
        assert "Calculator editing continues normally" in details
        assert "Supabase project saving is separate" in details
        assert page.locator("#calculator-recovery-warning").count() == 0
    finally:
        browser.close()
        manager.stop()



def test_legacy_recovery_arrays_remain_readable() -> None:
    manager, browser, page, _payload_data = _recovery_page(revision="legacy-recovery")
    try:
        snapshots = page.evaluate("window.ItineraryCalculator.storage.loadRecoverySnapshots()")
        legacy = [{key: value for key, value in snapshots[0].items() if key != "hash"}]
        page.evaluate(
            "legacy => window.localStorage.setItem(window.ItineraryCalculator.storage.recoveryStorageKey(), JSON.stringify(legacy))",
            legacy,
        )

        restored = page.evaluate("window.ItineraryCalculator.storage.loadRecoverySnapshots()")
        assert restored[0]["rows"][0]["travel_element"] == "Original service"
        assert len(restored[0]["hash"]) == 16
    finally:
        browser.close()
        manager.stop()
