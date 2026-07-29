from __future__ import annotations

import re

from support.calculator_browser_harness import (
    calculator_payload as _payload,
    open_calculator_browser_page as _browser_page,
    open_recovery_browser_page as _recovery_browser_page,
    recovery_payload as _recovery_payload,
)


def _recovery_page(*, revision: str = "recovery-test"):
    return _recovery_browser_page(revision=revision)


def test_local_version_history_restores_an_earlier_calculator_state() -> None:
    rows = [
        {"row_id": "1", "travel_element": "Original service", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="version-history"))
    page.set_default_timeout(3_000)
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        cell.click()
        page.keyboard.press("Control+a")
        page.keyboard.type("Updated service")
        page.keyboard.press("Tab")

        versions = page.locator('[data-action="version-history"]')
        page.evaluate("flushRecoverySnapshot()")
        assert int(re.search(r"\d+", versions.text_content()).group()) >= 2
        versions.evaluate("element => element.click()")
        version_items = page.locator("[data-version-id]")
        assert version_items.count() >= 2
        version_items.last.evaluate("element => element.click()")

        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Original service"
        assert page.locator("#calculator-sync-status").text_content().startswith("Recovered version from")
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
        page.evaluate(
            """() => {
                calculatorState.rows[0].gross_price_per_unit = '=10/0';
                markLocalDraft(false);
                flushLocalDraftSave();
            }"""
        )
        page.evaluate("window.ItineraryCalculator.storage.flushWrites()")
        page.evaluate(
            """async payload => {
                calculatorState = null;
                activeCell = null;
                activeBackendRevision = null;
                activeDraftStorageKey = null;
                hasLocalDraft = false;
                await initializeState(payload);
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
    manager, browser, page, _payload_data = _recovery_page(revision="compact-delta")
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
              calculatorState.dirty = true;
              calculatorState.recoverySnapshots = window.ItineraryCalculator.storage.saveRecoverySnapshot(
                calculatorState,
                activeBackendRevision,
                'edited'
              );
            }"""
        )
        stored = page.evaluate("JSON.parse(window.ItineraryCalculator.storage.readRecoveryRaw())")

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
        compact_size = page.evaluate("window.ItineraryCalculator.storage.readRecoveryRaw().length")
        assert compact_size < legacy_size

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


def test_budget_prunes_old_versions_before_current_draft() -> None:
    payload = _recovery_payload(revision="budget-prune")
    payload["browser_storage_contract"]["owners"]["calculator"]["max_namespace_bytes"] = 8_750
    manager, browser, page = _browser_page(payload)
    try:
        page.evaluate(
            """() => {
              calculatorState.rows[0].travel_element = 'Version two';
              window.ItineraryCalculator.storage.saveRecoverySnapshot(calculatorState, activeBackendRevision, 'second');
            }"""
        )
        long_comment = "current-draft-" + "z" * 8000
        saved = page.evaluate(
            """comment => {
              calculatorState.rows[0].comments = comment;
              return window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
            }""",
            long_comment,
        )

        assert saved is True
        draft = page.evaluate("JSON.parse(window.ItineraryCalculator.storage.readDraftRaw())")
        assert draft["rows"][0]["comments"] == long_comment
        assert page.evaluate("window.ItineraryCalculator.storage.readRecoveryRaw()") == ""
        assert page.evaluate("calculatorState.recoverySnapshots.length") == 0
        assert page.locator('[data-action="version-history"]').text_content().strip() == "Versions (0)"
        status = page.locator("#calculator-recovery-status")
        assert status.text_content() == "Local recovery reduced"
        status.click()
        assert "current Calculator draft" in page.locator(".calculator-local-recovery-info").text_content()
        assert page.locator("#calculator-recovery-warning").count() == 0
    finally:
        browser.close()
        manager.stop()


def test_oversized_draft_shows_one_quiet_unavailable_status() -> None:
    payload = _recovery_payload(revision="size-warning")
    payload["browser_storage_contract"]["owners"]["calculator"]["max_draft_bytes"] = 8_000
    manager, browser, page = _browser_page(payload)
    try:
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
        assert "Your current work remains open" in details
        assert "Supabase project saving is separate" in details
        assert page.locator("#calculator-recovery-warning").count() == 0
        recovered = page.evaluate(
            """async () => {
              calculatorState.rows[0].comments = 'small enough again';
              const saved = window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
              await window.ItineraryCalculator.storage.flushWrites();
              return {
                saved,
                pauseReason: window.ItineraryCalculator.require('storage.core').localRecoveryPauseReason(),
                stored: JSON.parse(window.ItineraryCalculator.storage.readDraftRaw()).rows[0].comments,
              };
            }"""
        )
        assert recovered == {
            "saved": True,
            "pauseReason": "",
            "stored": "small enough again",
        }
    finally:
        browser.close()
        manager.stop()


def test_legacy_recovery_arrays_remain_readable() -> None:
    manager, browser, page, _payload_data = _recovery_page(revision="legacy-recovery")
    try:
        legacy = [{
            "id": "legacy-1",
            "savedAt": 1_900_000_000_000,
            "rows": [{"row_id": "1", "travel_element": "Original service"}],
            "numberOfPax": None,
            "showAdvanced": False,
            "selectedRowIndex": 0,
            "activeCell": None,
            "selection": None,
            "columnWidths": {},
            "backendRevision": "legacy-recovery",
            "reason": "legacy",
        }]
        restored = page.evaluate(
            "legacy => window.ItineraryCalculator.require('storage.recovery').decodePayload(legacy)",
            legacy,
        )
        assert restored[0]["rows"][0]["travel_element"] == "Original service"
        assert len(restored[0]["hash"]) == 16
    finally:
        browser.close()
        manager.stop()



def test_local_draft_restores_trip_start_and_date_link_ownership() -> None:
    initial = _payload(
        [
            {
                "row_id": "1", "day": "Day 1", "from_date": "01.01.2026",
                "from_date_mode": "linked", "from_date_offset": 0,
                "supplier_currency": "NOK", "sales_currency": "EUR",
            },
            {
                "row_id": "2", "day": "Day 2", "from_date": "02.01.2026",
                "from_date_mode": "linked", "from_date_offset": 1,
                "supplier_currency": "NOK", "sales_currency": "EUR",
            },
        ],
        revision="trip-date-draft-remount",
        trip_start_date="2026-01-01",
    )
    manager, browser, page = _browser_page(initial)
    try:
        page.evaluate(
            """() => {
                setTripStartDate(calculatorState, '2026-02-01');
                markLocalDraft(false);
                flushLocalDraftSave();
            }"""
        )
        page.evaluate("window.ItineraryCalculator.storage.flushWrites()")
        page.evaluate(
            """async payload => {
                calculatorState = null;
                activeCell = null;
                activeBackendRevision = null;
                activeDraftStorageKey = null;
                hasLocalDraft = false;
                await initializeState(payload);
                rerender();
            }""",
            initial,
        )

        assert page.evaluate("calculatorState.tripStartDate") == "2026-02-01"
        assert page.evaluate("calculatorState.rows[1].from_date") == "02.02.2026"
        assert page.evaluate("calculatorState.rows[1].from_date_mode") == "linked"
        assert page.evaluate("calculatorState.rows[1].from_date_offset") == 1
        assert page.locator('[data-action="set-trip-start"]').input_value() == "2026-02-01"
    finally:
        browser.close()
        manager.stop()
