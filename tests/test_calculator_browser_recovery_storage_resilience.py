from __future__ import annotations

import re

from support.calculator_browser_harness import (
    open_recovery_browser_page as _recovery_browser_page,
    install_storage_quota as _install_storage_quota,
)


def _recovery_page(*, revision: str = "recovery-test"):
    return _recovery_browser_page(revision=revision)


def test_unavailable_storage_status_is_deduplicated_across_autosaves() -> None:
    manager, browser, page, _payload_data = _recovery_page(revision="quota-deduplicated")
    try:
        _install_storage_quota(page, 2_000)
        counts = page.evaluate(
            """() => {
              window.__recoveryStatusRefreshCount = 0;
              const originalRefresh = refreshRecoveryStatusOnly;
              refreshRecoveryStatusOnly = () => {
                window.__recoveryStatusRefreshCount += 1;
                originalRefresh();
              };
              calculatorState.rows[0].comments = 'q'.repeat(12000);
              const firstSaved = window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
              const afterFirst = window.__recoveryStatusRefreshCount;
              const secondSaved = window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
              return {firstSaved, secondSaved, afterFirst, afterSecond: window.__recoveryStatusRefreshCount};
            }"""
        )

        assert counts["firstSaved"] is False
        assert counts["secondSaved"] is False
        assert counts["afterFirst"] >= 1
        assert counts["afterSecond"] == counts["afterFirst"]
        assert page.locator("#calculator-recovery-status").count() == 1
    finally:
        browser.close()
        manager.stop()


def test_blocked_storage_does_not_interrupt_calculator_editing() -> None:
    manager, browser, page, _payload_data = _recovery_page(revision="blocked-storage")
    try:
        result = page.evaluate(
            """() => {
              window.localStorage.getItem = () => { throw new DOMException('Blocked', 'SecurityError'); };
              window.localStorage.setItem = () => { throw new DOMException('Blocked', 'SecurityError'); };
              window.localStorage.removeItem = () => { throw new DOMException('Blocked', 'SecurityError'); };
              calculatorState.rows[0].travel_element = 'Editing still works';
              markLocalDraft();
              flushLocalDraftSave();
              return {
                value: calculatorState.rows[0].travel_element,
                dirty: calculatorState.dirty,
                status: calculatorState.recoveryStatus.state,
              };
            }"""
        )

        assert result == {"value": "Editing still works", "dirty": True, "status": "unavailable"}
        assert page.locator("#calculator-recovery-status").text_content() == "Local recovery unavailable"
    finally:
        browser.close()
        manager.stop()


def test_clear_local_recovery_data_removes_current_draft_and_versions_only() -> None:
    manager, browser, page, payload = _recovery_page(revision="clear-local-recovery")
    try:
        page.evaluate(
            """() => {
              calculatorState.rows[0].travel_element = 'Unsaved current value';
              markLocalDraft(false);
              flushLocalDraftSave();
              window.localStorage.setItem('unrelated.application.key', 'keep');
              window.confirm = () => true;
            }"""
        )
        assert page.evaluate("key => window.localStorage.getItem(key) !== null", payload["draft_storage_key"])
        assert page.evaluate("window.localStorage.getItem(window.ItineraryCalculator.storage.recoveryStorageKey()) !== null")

        page.get_by_role("button", name=re.compile(r"Versions \(\d+\)")).click()
        page.get_by_role("button", name="Clear local recovery data").click()

        assert page.evaluate("key => window.localStorage.getItem(key)", payload["draft_storage_key"]) is None
        assert page.evaluate("window.localStorage.getItem(window.ItineraryCalculator.storage.recoveryStorageKey())") is None
        assert page.evaluate("window.localStorage.getItem('unrelated.application.key')") == "keep"
        assert page.evaluate("calculatorState.rows[0].travel_element") == "Unsaved current value"
        assert page.evaluate("calculatorState.dirty") is True
        assert page.get_by_role("button", name="Versions (0)").count() == 1

        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            payload,
        )
        assert page.evaluate("key => window.localStorage.getItem(key)", payload["draft_storage_key"]) is None
        page.wait_for_timeout(2800)
        assert page.evaluate("key => window.localStorage.getItem(key)", payload["draft_storage_key"]) is None
        assert page.evaluate("window.localStorage.getItem(window.ItineraryCalculator.storage.recoveryStorageKey())") is None

        page.evaluate("calculatorState.rows[0].comments = 'new edit'; markLocalDraft(false); flushLocalDraftSave();")
        assert page.evaluate("key => window.localStorage.getItem(key) !== null", payload["draft_storage_key"])
    finally:
        browser.close()
        manager.stop()


def test_obsolete_calculator_namespaces_are_cleaned_without_touching_recent_or_unrelated_data() -> None:
    manager, browser, page, _payload_data = _recovery_page(revision="namespace-cleanup")
    try:
        result = page.evaluate(
            """() => {
              const oldBase = 'itineraryCalculatorBrowserDraft.v3.project:old';
              const recentBase = 'itineraryCalculatorBrowserDraft.v3.project:recent';
              const oldSavedAt = Date.now() - window.ItineraryCalculator.require('storage.core').draftMaxAgeMs - 1000;
              window.localStorage.setItem(oldBase, JSON.stringify({savedAt: oldSavedAt, rows: [{}]}));
              window.localStorage.setItem(`${oldBase}.versions`, JSON.stringify([{id: 'old', savedAt: oldSavedAt, rows: [{}]}]));
              window.localStorage.setItem(recentBase, JSON.stringify({savedAt: Date.now(), rows: [{}]}));
              window.localStorage.setItem(`${recentBase}.versions`, JSON.stringify([{id: 'recent', savedAt: Date.now(), rows: [{}]}]));
              window.localStorage.setItem('unrelated.application.key', 'keep');
              window.ItineraryCalculator.require('storage.core').cleanupObsoleteNamespaces();
              return {
                oldDraft: window.localStorage.getItem(oldBase),
                oldVersions: window.localStorage.getItem(`${oldBase}.versions`),
                recentDraft: window.localStorage.getItem(recentBase),
                recentVersions: window.localStorage.getItem(`${recentBase}.versions`),
                unrelated: window.localStorage.getItem('unrelated.application.key'),
              };
            }"""
        )

        assert result["oldDraft"] is None
        assert result["oldVersions"] is None
        assert result["recentDraft"] is not None
        assert result["recentVersions"] is not None
        assert result["unrelated"] == "keep"
    finally:
        browser.close()
        manager.stop()


def test_quota_prunes_inactive_project_versions_before_active_versions() -> None:
    manager, browser, page, payload = _recovery_page(revision="inactive-quota-prune")
    try:
        result = page.evaluate(
            """() => {
              const inactiveBase = 'itineraryCalculatorBrowserDraft.v3.project:inactive';
              window.localStorage.setItem(inactiveBase, JSON.stringify({savedAt: Date.now() - 1000, rows: [{}]}));
              window.localStorage.setItem(`${inactiveBase}.versions`, JSON.stringify([{id: 'inactive', savedAt: Date.now() - 1000, rows: [{}]}]));
              const originalSetItem = window.localStorage.setItem.bind(window.localStorage);
              window.localStorage.setItem = (key, value) => {
                if (String(key) === window.ItineraryCalculator.storage.getDraftStorageKey() && window.localStorage.getItem(`${inactiveBase}.versions`) !== null) {
                  throw new DOMException('Storage quota exceeded', 'QuotaExceededError');
                }
                originalSetItem(String(key), String(value));
              };
              calculatorState.rows[0].comments = 'active draft';
              const saved = window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
              return {
                saved,
                activeDraft: window.localStorage.getItem(window.ItineraryCalculator.storage.getDraftStorageKey()),
                activeVersions: window.localStorage.getItem(window.ItineraryCalculator.storage.recoveryStorageKey()),
                inactiveDraft: window.localStorage.getItem(inactiveBase),
                inactiveVersions: window.localStorage.getItem(`${inactiveBase}.versions`),
                status: calculatorState.recoveryStatus,
              };
            }"""
        )

        assert result["saved"] is True
        assert result["activeDraft"] is not None
        assert result["activeVersions"] is not None
        assert result["inactiveDraft"] is not None
        assert result["inactiveVersions"] is None
        assert result["status"]["state"] == "reduced"
        assert "inactive projects" in result["status"]["detail"]
    finally:
        browser.close()
        manager.stop()


def test_quota_keeps_newest_active_versions_when_space_allows() -> None:
    manager, browser, page, _payload_data = _recovery_page(revision="active-version-retention")
    try:
        result = page.evaluate(
            """() => {
              for (let index = 1; index <= 3; index += 1) {
                calculatorState.rows[0].travel_element = `Version ${index}`;
                window.ItineraryCalculator.storage.saveRecoverySnapshot(calculatorState, activeBackendRevision, `version-${index}`);
              }
              const before = window.ItineraryCalculator.storage.loadRecoverySnapshots();
              const newestId = before[0].id;
              const originalSetItem = window.localStorage.setItem.bind(window.localStorage);
              window.localStorage.setItem = (key, value) => {
                if (String(key) === window.ItineraryCalculator.storage.getDraftStorageKey()) {
                  const stored = window.localStorage.getItem(window.ItineraryCalculator.storage.recoveryStorageKey());
                  const count = stored ? window.ItineraryCalculator.require('storage.recovery').decodePayload(JSON.parse(stored)).length : 0;
                  if (count > 1) throw new DOMException('Storage quota exceeded', 'QuotaExceededError');
                }
                originalSetItem(String(key), String(value));
              };
              calculatorState.rows[0].comments = 'current draft';
              const saved = window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
              const after = window.ItineraryCalculator.storage.loadRecoverySnapshots();
              return {
                saved,
                beforeCount: before.length,
                afterCount: after.length,
                newestId,
                retainedId: after[0]?.id || '',
              };
            }"""
        )

        assert result["saved"] is True
        assert result["beforeCount"] >= 3
        assert result["afterCount"] == 1
        assert result["retainedId"] == result["newestId"]
    finally:
        browser.close()
        manager.stop()



def test_project_namespace_switch_keeps_recovery_isolated_and_restorable() -> None:
    manager, browser, page, project_a = _recovery_page(revision="project-a")
    try:
        page.evaluate(
            """() => {
              calculatorState.rows[0].travel_element = 'Unsaved Project A';
              markLocalDraft(false);
              flushLocalDraftSave();
            }"""
        )
        project_b = {
            **project_a,
            "rows": [
                {
                    "row_id": "1",
                    "travel_element": "Saved Project B",
                    "supplier_currency": "NOK",
                    "sales_currency": "EUR",
                }
            ],
            "state_revision": "project-b",
            "draft_storage_key": "itineraryCalculatorBrowserDraft.v3.project:project-b",
        }
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            project_b,
        )
        page.wait_for_selector('td[data-row-index="0"][data-key="travel_element"]')

        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Saved Project B"
        assert page.evaluate(
            "key => JSON.parse(window.localStorage.getItem(key)).rows[0].travel_element",
            project_a["draft_storage_key"],
        ) == "Unsaved Project A"

        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            project_a,
        )
        page.wait_for_function("calculatorState.rows[0].travel_element === 'Unsaved Project A'")

        assert page.locator('td[data-row-index="0"][data-key="travel_element"]').text_content().strip() == "Unsaved Project A"
        assert page.evaluate("window.ItineraryCalculator.storage.getDraftStorageKey()") == project_a["draft_storage_key"]
    finally:
        browser.close()
        manager.stop()
