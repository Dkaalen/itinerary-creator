from __future__ import annotations

import re

from support.calculator_browser_harness import (
    calculator_payload,
    open_blank_calculator_browser_page,
    open_recovery_browser_page,
    recovery_payload,
)


def _dispatch(page, payload) -> None:
    page.evaluate(
        "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
        payload,
    )
    page.wait_for_selector('td[data-key="travel_element"]')


def test_unavailable_indexeddb_does_not_interrupt_calculator_editing() -> None:
    manager, browser, page = open_blank_calculator_browser_page()
    try:
        page.evaluate("Object.defineProperty(window, 'indexedDB', {value: null, configurable: true})")
        payload = recovery_payload(revision="blocked-indexeddb")
        _dispatch(page, payload)

        result = page.evaluate(
            """() => {
              calculatorState.rows[0].travel_element = 'Editing still works';
              markLocalDraft(false);
              flushLocalDraftSave();
              return {
                value: calculatorState.rows[0].travel_element,
                dirty: calculatorState.dirty,
                status: calculatorState.recoveryStatus.state,
                localKeys: [...Array(localStorage.length)].map((_, index) => localStorage.key(index)),
              };
            }"""
        )

        assert result == {
            "value": "Editing still works",
            "dirty": True,
            "status": "unavailable",
            "localKeys": [],
        }
        assert page.locator("#calculator-recovery-status").text_content() == "Local recovery unavailable"
    finally:
        browser.close()
        manager.stop()


def test_failed_indexeddb_write_pauses_future_writes_without_repeated_status_refresh() -> None:
    manager, browser, page, _payload = open_recovery_browser_page(revision="write-failure")
    try:
        result = page.evaluate(
            """async () => {
              window.__recoveryStatusRefreshCount = 0;
              const originalRefresh = refreshRecoveryStatusOnly;
              refreshRecoveryStatusOnly = () => {
                window.__recoveryStatusRefreshCount += 1;
                originalRefresh();
              };
              window.__failFakeIndexedDbWrites = true;
              calculatorState.rows[0].comments = 'first';
              const firstQueued = window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
              await window.ItineraryCalculator.storage.flushWrites();
              const attemptsAfterFailure = Number(window.__fakeIndexedDbPutAttemptCount || 0);
              const afterFirst = window.__recoveryStatusRefreshCount;

              calculatorState.rows[0].comments = 'second edit remains open';
              markLocalDraft(false);
              flushLocalDraftSave();
              await window.ItineraryCalculator.storage.flushWrites();
              return {
                firstQueued,
                attemptsAfterFailure,
                attemptsAfterEdit: Number(window.__fakeIndexedDbPutAttemptCount || 0),
                afterFirst,
                afterSecond: window.__recoveryStatusRefreshCount,
                status: calculatorState.recoveryStatus.state,
                pauseReason: window.ItineraryCalculator.require('storage.core').localRecoveryPauseReason(),
                persistedDraft: window.ItineraryCalculator.storage.readDraftRaw(),
                currentValue: calculatorState.rows[0].comments,
                dirty: calculatorState.dirty,
              };
            }"""
        )

        assert result["firstQueued"] is True
        assert result["attemptsAfterFailure"] >= 1
        assert result["attemptsAfterEdit"] == result["attemptsAfterFailure"]
        assert result["status"] == "unavailable"
        assert result["pauseReason"] == "failure"
        assert result["persistedDraft"] == ""
        assert result["currentValue"] == "second edit remains open"
        assert result["dirty"] is True
        assert result["afterFirst"] >= 1
        assert result["afterSecond"] == result["afterFirst"]
        assert page.locator("#calculator-recovery-status").count() == 1
    finally:
        browser.close()
        manager.stop()


def test_failed_overwrite_restores_the_last_persisted_calculator_draft() -> None:
    manager, browser, page, _payload = open_recovery_browser_page(revision="failed-overwrite")
    try:
        result = page.evaluate(
            """async () => {
              calculatorState.rows[0].comments = 'persisted value';
              const firstQueued = window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
              await window.ItineraryCalculator.storage.flushWrites();
              const persistedBefore = JSON.parse(window.ItineraryCalculator.storage.readDraftRaw()).rows[0].comments;

              window.__failFakeIndexedDbWrites = true;
              calculatorState.rows[0].comments = 'failed replacement';
              const failedQueued = window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
              await window.ItineraryCalculator.storage.flushWrites();
              return {
                firstQueued,
                failedQueued,
                persistedBefore,
                persistedAfter: JSON.parse(window.ItineraryCalculator.storage.readDraftRaw()).rows[0].comments,
                currentValue: calculatorState.rows[0].comments,
                pauseReason: window.ItineraryCalculator.require('storage.core').localRecoveryPauseReason(),
              };
            }"""
        )

        assert result == {
            "firstQueued": True,
            "failedQueued": True,
            "persistedBefore": "persisted value",
            "persistedAfter": "persisted value",
            "currentValue": "failed replacement",
            "pauseReason": "failure",
        }
    finally:
        browser.close()
        manager.stop()


def test_clear_local_recovery_removes_only_owned_records_and_keeps_current_work() -> None:
    manager, browser, page, _payload = open_recovery_browser_page(revision="clear-local-recovery")
    try:
        result = page.evaluate(
            """async () => {
              calculatorState.rows[0].travel_element = 'Unsaved current value';
              markLocalDraft(false);
              flushLocalDraftSave();
              flushRecoverySnapshot('manual');
              await window.ItineraryCalculator.storage.flushWrites();
              localStorage.setItem('unrelated.application.key', 'keep');
              const before = {
                draft: window.ItineraryCalculator.storage.readDraftRaw(),
                recovery: window.ItineraryCalculator.storage.readRecoveryRaw(),
              };
              const cleared = window.ItineraryCalculator.storage.clearLocalRecoveryData();
              await window.ItineraryCalculator.storage.flushWrites();
              return {
                before,
                cleared,
                afterDraft: window.ItineraryCalculator.storage.readDraftRaw(),
                afterRecovery: window.ItineraryCalculator.storage.readRecoveryRaw(),
                unrelated: localStorage.getItem('unrelated.application.key'),
                value: calculatorState.rows[0].travel_element,
                dirty: calculatorState.dirty,
              };
            }"""
        )

        assert result["before"]["draft"]
        assert result["before"]["recovery"]
        assert result["cleared"] is True
        assert result["afterDraft"] == ""
        assert result["afterRecovery"] == ""
        assert result["unrelated"] == "keep"
        assert result["value"] == "Unsaved current value"
        assert result["dirty"] is True

        page.evaluate(
            """async () => {
              calculatorState.rows[0].comments = 'new edit';
              markLocalDraft(false);
              flushLocalDraftSave();
              await window.ItineraryCalculator.storage.flushWrites();
            }"""
        )
        assert page.evaluate("window.ItineraryCalculator.storage.readDraftRaw() !== ''") is True
    finally:
        browser.close()
        manager.stop()


def test_legacy_localstorage_migrates_to_indexeddb_and_stale_namespaces_are_removed() -> None:
    manager, browser, page = open_blank_calculator_browser_page()
    try:
        payload = calculator_payload([], revision="migration")
        prefix = payload["browser_storage_contract"]["owners"]["calculator"]["current_prefix"]
        active = f"{prefix}project:active"
        old = f"{prefix}project:old"
        recent = f"{prefix}project:recent"
        payload["draft_storage_key"] = active
        page.evaluate(
            """({active, old, recent, maxAge}) => {
              const oldSavedAt = Date.now() - maxAge - 1000;
              localStorage.setItem(old, JSON.stringify({savedAt: oldSavedAt, rows: [{}]}));
              localStorage.setItem(`${old}.versions`, JSON.stringify([{id: 'old', savedAt: oldSavedAt, rows: [{}]}]));
              localStorage.setItem(recent, JSON.stringify({savedAt: Date.now(), rows: [{}]}));
              localStorage.setItem(`${recent}.versions`, JSON.stringify([{id: 'recent', savedAt: Date.now(), rows: [{}]}]));
              localStorage.setItem(active, JSON.stringify({savedAt: Date.now(), rows: [{}]}));
              localStorage.setItem('unrelated.application.key', 'keep');
            }""",
            {
                "active": active,
                "old": old,
                "recent": recent,
                "maxAge": payload["browser_storage_contract"]["owners"]["calculator"]["max_age_ms"],
            },
        )
        _dispatch(page, payload)
        page.evaluate("window.ItineraryCalculator.storage.flushWrites()")

        records = page.evaluate("window.ItineraryCalculator.storage.debugRecords()")
        namespaces = {record["namespace"] for record in records}
        assert old not in namespaces
        assert active in namespaces
        assert recent in namespaces
        assert page.evaluate("localStorage.getItem('unrelated.application.key')") == "keep"
        assert page.evaluate(
            """prefix => [...Array(localStorage.length)]
              .map((_, index) => localStorage.key(index))
              .every(key => !String(key || '').startsWith(prefix))""",
            prefix,
        ) is True
    finally:
        browser.close()
        manager.stop()


def test_paired_recovery_versions_count_toward_global_namespace_budget() -> None:
    manager, browser, page = open_blank_calculator_browser_page()
    try:
        payload = calculator_payload([], revision="paired-budget")
        config = payload["browser_storage_contract"]["owners"]["calculator"]
        config["max_total_bytes"] = 3_000
        config["max_namespaces"] = 3
        prefix = config["current_prefix"]
        old = f"{prefix}project:old-paired"
        active = f"{prefix}project:active-paired"
        payload["draft_storage_key"] = active
        page.evaluate(
            """({old, active}) => {
              localStorage.setItem(old, JSON.stringify({savedAt: Date.now() - 1000, rows: [{}]}));
              localStorage.setItem(`${old}.versions`, JSON.stringify([{id: 'old', savedAt: Date.now() - 1000, rows: [{comments: 'x'.repeat(4000)}]}]));
              localStorage.setItem(active, JSON.stringify({savedAt: Date.now(), rows: [{}]}));
            }""",
            {"old": old, "active": active},
        )
        _dispatch(page, payload)
        page.evaluate("window.ItineraryCalculator.storage.flushWrites()")

        records = page.evaluate("window.ItineraryCalculator.storage.debugRecords()")
        namespaces = {record["namespace"] for record in records}
        assert old not in namespaces
        assert active in namespaces
    finally:
        browser.close()
        manager.stop()


def test_active_draft_growth_prunes_old_namespaces_after_write() -> None:
    manager, browser, page = open_blank_calculator_browser_page()
    try:
        payload = calculator_payload([], revision="active-growth-budget")
        config = payload["browser_storage_contract"]["owners"]["calculator"]
        config["max_total_bytes"] = 55_000
        config["max_namespaces"] = 3
        prefix = config["current_prefix"]
        old = f"{prefix}project:old-growth"
        active = f"{prefix}project:active-growth"
        payload["draft_storage_key"] = active
        page.evaluate(
            """old => {
              localStorage.setItem(old, JSON.stringify({
                savedAt: Date.now() - 1000,
                rows: [{comments: 'o'.repeat(9000)}],
              }));
            }""",
            old,
        )
        _dispatch(page, payload)
        page.evaluate("window.ItineraryCalculator.storage.flushWrites()")
        assert old in {
            record["namespace"]
            for record in page.evaluate("window.ItineraryCalculator.storage.debugRecords()")
        }

        result = page.evaluate(
            """async ({active, maxBytes}) => {
              calculatorState.rows[0].comments = 'a'.repeat(14000);
              markLocalDraft(false);
              flushLocalDraftSave();
              await window.ItineraryCalculator.storage.flushWrites();
              const records = window.ItineraryCalculator.storage.debugRecords();
              return {
                namespaces: [...new Set(records.map(record => record.namespace))],
                totalBytes: records.reduce((total, record) => total + Number(record.bytes || 0), 0),
                maxBytes,
                active,
              };
            }""",
            {"active": active, "maxBytes": config["max_total_bytes"]},
        )

        assert old not in result["namespaces"]
        assert active in result["namespaces"]
        assert result["totalBytes"] <= result["maxBytes"]
    finally:
        browser.close()
        manager.stop()


def test_project_namespace_switch_keeps_recovery_isolated_and_restorable() -> None:
    manager, browser, page, project_a = open_recovery_browser_page(revision="project-a")
    try:
        page.evaluate(
            """async () => {
              calculatorState.rows[0].travel_element = 'Unsaved Project A';
              markLocalDraft(false);
              flushLocalDraftSave();
              await window.ItineraryCalculator.storage.flushWrites();
            }"""
        )
        project_b = {
            **project_a,
            "rows": [{
                "row_id": "1",
                "travel_element": "Saved Project B",
                "supplier_currency": "NOK",
                "sales_currency": "EUR",
            }],
            "state_revision": "project-b",
            "draft_storage_key": "itineraryCalculatorBrowserDraft.v3.project:project-b",
        }
        _dispatch(page, project_b)
        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Saved Project B"
        stored_a = page.evaluate(
            """key => {
              const record = window.ItineraryCalculator.storage.debugRecords()
                .find(item => item.namespace === key && item.kind === 'draft');
              return record ? JSON.parse(record.payload).rows[0].travel_element : '';
            }""",
            project_a["draft_storage_key"],
        )
        assert stored_a == "Unsaved Project A"

        _dispatch(page, project_a)
        page.wait_for_function("calculatorState.rows[0].travel_element === 'Unsaved Project A'")
        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Unsaved Project A"
    finally:
        browser.close()
        manager.stop()


def test_clean_render_performs_no_recovery_write_until_first_edit() -> None:
    manager, browser, page, _payload = open_recovery_browser_page(revision="clean-render")
    try:
        assert page.evaluate("Number(window.__fakeIndexedDbPutCount || 0)") == 0
        assert page.evaluate("window.ItineraryCalculator.storage.debugRecords().length") == 0

        result = page.evaluate(
            """async () => {
              calculatorState.rows[0].travel_element = 'First local edit';
              markLocalDraft(false);
              await window.ItineraryCalculator.storage.flushWrites();
              return {
                puts: Number(window.__fakeIndexedDbPutCount || 0),
                versions: calculatorState.recoverySnapshots.length,
                reason: calculatorState.recoverySnapshots[0]?.reason || '',
              };
            }"""
        )
        assert result == {"puts": 1, "versions": 1, "reason": "baseline"}
    finally:
        browser.close()
        manager.stop()
