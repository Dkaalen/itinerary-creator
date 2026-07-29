from __future__ import annotations

import json
import re
from pathlib import Path

from tests.support.visual_editor_browser_harness import (
    open_bootstrapped_visual_editor_browser_page,
    open_visual_editor_browser_page,
    visual_editor_bootstrap_script_names,
    visual_editor_payload,
)


FRONTEND = Path("visual_editor_component/frontend")
JS_ROOT = FRONTEND / "js"


def test_visual_editor_has_one_explicit_namespace_and_no_document_write_loader() -> None:
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    all_js = "\n".join(path.read_text(encoding="utf-8") for path in JS_ROOT.glob("*.js"))

    assert 'src="js/editor_namespace.js" defer' in index
    assert 'src="js/editor_bootstrap.js" defer' in index
    assert "document.write" not in all_js
    assert "window.visualEditorCommands" not in all_js
    assert "window.CONTROLLED_EDITOR_STYLE_REGISTRY" not in all_js
    assert not (JS_ROOT / "editor_assets.js").exists()
    assert not (JS_ROOT / "commands.js").exists()
    assert "Object.defineProperty(window, 'ItineraryVisualEditor'" in all_js
    assert re.findall(r"Object\.defineProperty\(window,\s*'([^']+)'", all_js) == ["ItineraryVisualEditor"]


def test_visual_editor_registers_responsibility_modules() -> None:
    registrations = {}
    for path in JS_ROOT.glob("*.js"):
        for name in re.findall(r"ItineraryVisualEditor\.define\('([^']+)'", path.read_text(encoding="utf-8")):
            assert name not in registrations, f"duplicate module registration: {name}"
            registrations[name] = path.name

    assert registrations == {
        "state": "state.js",
        "draftStorage": "editor_draft_storage.js",
        "drafts": "editor_local_draft.js",
        "payload": "serialization.js",
        "stylePresets": "style_preset_data.js",
        "renderer": "render.js",
        "pages": "editor_page_actions.js",
        "autosave": "editing.js",
        "bridge": "streamlit_bridge.js",
    }



def test_real_visual_editor_bootstrap_loads_manifest_without_runtime_errors() -> None:
    manager, browser, page, requested_assets, page_errors = open_bootstrapped_visual_editor_browser_page()
    try:
        assert page.evaluate("window.ItineraryVisualEditor.list()") == [
            "state",
            "draftStorage",
            "drafts",
            "payload",
            "stylePresets",
            "renderer",
            "pages",
            "autosave",
            "bridge",
        ]
        requested_js = [asset.removeprefix("js/") for asset in requested_assets if asset.startswith("js/")]
        assert requested_js == [
            "editor_namespace.js",
            "editor_bootstrap.js",
            *visual_editor_bootstrap_script_names(),
        ]
        assert page_errors == []
    finally:
        browser.close()
        manager.stop()

def test_visual_editor_namespace_rejects_duplicate_modules_in_chromium() -> None:
    manager, browser, page, _payload = open_visual_editor_browser_page()
    try:
        modules = page.evaluate("window.ItineraryVisualEditor.list()")
        duplicate_error = page.evaluate(
            """() => {
              try {
                window.ItineraryVisualEditor.define('state', {});
                return '';
              } catch (error) {
                return error.message;
              }
            }"""
        )

        assert modules == [
            "state",
            "draftStorage",
            "drafts",
            "payload",
            "stylePresets",
            "renderer",
            "pages",
            "autosave",
            "bridge",
        ]
        assert duplicate_error == "Visual editor module already defined: state"
    finally:
        browser.close()
        manager.stop()



def test_visual_editor_image_change_updates_state_and_save_delta_in_chromium() -> None:
    payload = visual_editor_payload()
    payload["workflow"]["pictures_added"] = True
    payload["days"][0]["image"] = {
        "mode": "auto",
        "path": "",
        "name": "Oslo",
        "data_uri": "data:image/png;base64,AAAA",
        "auto_data_uri": "data:image/png;base64,AAAA",
        "auto_name": "Oslo",
        "crop_focus": "top",
        "options": [
            {
                "path": "oslo-evening.webp",
                "name": "Oslo evening",
                "preview_data_uri": "data:image/png;base64,BBBB",
            }
        ],
    }

    manager, browser, page, _payload = open_visual_editor_browser_page(payload)
    try:
        focus = page.locator('[data-img-focus="0"]')
        assert focus.count() == 1
        focus.select_option("center")
        page.wait_for_function(
            "window.ItineraryVisualEditor.require('state').snapshot().model.days[0].image.crop_focus === 'center'"
        )
        snapshot = page.evaluate("window.ItineraryVisualEditor.require('state').snapshot()")
        assert "days.0.image" in snapshot["touchedKeys"]
        assert snapshot["model"]["days"][0]["image"]["crop_focus"] == "center"
        assert "center" in (page.locator('.image-stage[data-day-index="0"] img').get_attribute("style") or "")

        page.locator("#saveBtn").click()
        page.wait_for_function(
            "window.__visualEditorMessages.some(message => message.type === 'streamlit:setComponentValue')"
        )
        serialized = page.evaluate(
            """() => window.__visualEditorMessages
              .filter(message => message.type === 'streamlit:setComponentValue')
              .at(-1).value"""
        )
        saved = json.loads(serialized)
        assert saved["days"][0]["image"]["crop_focus"] == "center"
        assert "data_uri" not in saved["days"][0]["image"]
    finally:
        browser.close()
        manager.stop()

def test_visual_editor_page_edit_save_reset_and_hidden_page_flow_in_chromium() -> None:
    manager, browser, page, payload = open_visual_editor_browser_page()
    try:
        title = page.locator('[data-edit-key="days.0.title"]')
        assert title.inner_text() == "Arrival in Oslo"

        title.evaluate(
            """element => {
              element.textContent = 'Edited arrival title';
              element.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
            }"""
        )
        page.wait_for_function(
            "window.ItineraryVisualEditor.require('state').snapshot().touchedKeys.includes('days.0.title')"
        )
        page.wait_for_timeout(750)
        local_draft = page.evaluate(
            """async () => {
              const drafts = window.ItineraryVisualEditor.require('drafts');
              await drafts.flush();
              return drafts.read();
            }"""
        )
        assert local_draft
        assert "Edited arrival title" in local_draft

        page.locator("#saveBtn").click()
        page.wait_for_function(
            "window.__visualEditorMessages.some(message => message.type === 'streamlit:setComponentValue')"
        )
        serialized = page.evaluate(
            """() => window.__visualEditorMessages
              .filter(message => message.type === 'streamlit:setComponentValue')
              .at(-1).value"""
        )
        saved = json.loads(serialized)
        assert saved["days"][0]["title"] == "Edited arrival title"

        page.evaluate("window.ItineraryVisualEditor.require('pages').hide('summary')")
        assert page.evaluate(
            "window.ItineraryVisualEditor.require('state').snapshot().model.document_pages"
            ".find(page => page.page_id === 'summary').is_hidden"
        ) is True
        assert page.locator('[data-page-id="summary"]').count() == 0

        page.evaluate("window.ItineraryVisualEditor.require('pages').restore('summary')")
        assert page.evaluate(
            "window.ItineraryVisualEditor.require('state').snapshot().model.document_pages"
            ".find(page => page.page_id === 'summary').is_hidden"
        ) is False
        assert page.locator('[data-page-id="summary"]').count() == 1

        page.evaluate("document.getElementById('resetBtn').click()")
        assert page.locator('[data-edit-key="days.0.title"]').inner_text() == payload["days"][0]["title"]
    finally:
        browser.close()
        manager.stop()



def test_visual_editor_picture_transition_keeps_generated_day_pages_visible_in_chromium() -> None:
    payload = visual_editor_payload()
    manager, browser, page, _payload = open_visual_editor_browser_page(payload)
    try:
        title = page.locator('[data-edit-key="days.0.title"]')
        title.evaluate(
            """element => {
              element.textContent = 'Edited arrival title';
              element.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
            }"""
        )
        page.wait_for_function(
            "window.ItineraryVisualEditor.require('state').snapshot().touchedKeys.includes('days.0.title')"
        )

        assert page.evaluate(
            "window.ItineraryVisualEditor.require('autosave').saveChanges('apply-before-pictures')"
        ) is True
        page.evaluate(
            """async () => {
              await window.ItineraryVisualEditor.require('drafts').flush();
            }"""
        )

        picture_payload = json.loads(json.dumps(payload))
        picture_payload["workflow"]["pictures_added"] = True
        for day in picture_payload["days"]:
            day["image"] = {
                "mode": "auto",
                "data_uri": "data:image/png;base64,AAAA",
                "auto_data_uri": "data:image/png;base64,AAAA",
                "crop_focus": "top",
            }

        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', "
            "{data: {type: 'streamlit:render', args: {payload}}}))",
            picture_payload,
        )
        page.wait_for_function(
            "window.ItineraryVisualEditor.require('state').snapshot().model.workflow.pictures_added === true"
        )

        assert page.locator(".day-page").count() == len(payload["days"])
        assert page.locator('[data-page-id="day-day-1"]').count() == 1
        assert page.locator('[data-page-id="day-day-2"]').count() == 1
        assert page.locator('[data-edit-key="days.0.title"]').inner_text() == "Edited arrival title"

        generated_pages = page.evaluate(
            "window.ItineraryVisualEditor.require('state').snapshot().model.document_pages"
            ".filter(page => page.page_type === 'generated_day')"
        )
        assert [item["is_hidden"] for item in generated_pages] == [False, False]
    finally:
        browser.close()
        manager.stop()

def test_visual_editor_indexeddb_failure_keeps_current_edit_and_reports_paused_recovery() -> None:
    manager, browser, page, _payload = open_visual_editor_browser_page()
    try:
        title = page.locator('[data-edit-key="days.0.title"]')
        title.evaluate(
            """element => {
              element.textContent = 'Persisted visual title';
              element.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
            }"""
        )
        page.evaluate(
            """async () => {
              const drafts = window.ItineraryVisualEditor.require('drafts');
              drafts.persist();
              await drafts.flush();
            }"""
        )
        page.evaluate("window.__failFakeIndexedDbWrites = true")
        title.evaluate(
            """element => {
              element.textContent = 'Unsaved title after storage failure';
              element.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
            }"""
        )
        result = page.evaluate(
            """async () => {
              const drafts = window.ItineraryVisualEditor.require('drafts');
              drafts.persist();
              await drafts.flush();
              return {
                title: window.ItineraryVisualEditor.require('state').snapshot().model.days[0].title,
                detail: document.getElementById('saveStatusDetail')?.textContent || '',
                localKeys: [...Array(localStorage.length)].map((_, index) => localStorage.key(index)),
                attempts: Number(window.__fakeIndexedDbPutAttemptCount || 0),
                pauseReason: window.ItineraryVisualEditor.require('draftStorage').pauseReason(),
                persistedDraft: drafts.read(),
              };
            }"""
        )

        assert result["title"] == "Unsaved title after storage failure"
        assert "Browser recovery paused" in result["detail"]
        assert result["attempts"] >= 1
        assert result["pauseReason"] == "failure"
        assert "Persisted visual title" in result["persistedDraft"]
        assert "Unsaved title after storage failure" not in result["persistedDraft"]
        assert not any(str(key or "").startswith("itinerary-visual-editor-draft:") for key in result["localKeys"])

        next_payload = visual_editor_payload()
        next_payload["draft_id"] = "visual-editor-after-failure"
        next_payload["meta"]["source_signature"] = "visual-editor-after-failure-signature"
        after_switch = page.evaluate(
            """async (payload) => {
              const storage = window.ItineraryVisualEditor.require('draftStorage');
              await storage.prepare(payload);
              const queued = storage.write(JSON.stringify({saved_at: Date.now(), model: {title: 'second'}}));
              await storage.flush();
              return {
                queued,
                attempts: Number(window.__fakeIndexedDbPutAttemptCount || 0),
                pauseReason: storage.pauseReason(),
                currentTitle: window.ItineraryVisualEditor.require('state').snapshot().model.days[0].title,
              };
            }""",
            next_payload,
        )
        assert after_switch == {
            "queued": False,
            "attempts": result["attempts"],
            "pauseReason": "failure",
            "currentTitle": "Unsaved title after storage failure",
        }
    finally:
        browser.close()
        manager.stop()


def test_visual_editor_size_pause_resets_for_a_different_project() -> None:
    oversized_payload = visual_editor_payload()
    oversized_payload["draft_id"] = "visual-editor-oversized"
    oversized_payload["browser_storage_contract"]["owners"]["visual_editor"]["max_draft_bytes"] = 20_000
    manager, browser, page, _payload = open_visual_editor_browser_page(oversized_payload)
    try:
        page.locator('[data-edit-key="days.0.title"]').evaluate(
            """element => {
              element.textContent = 'x'.repeat(50000);
              element.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
            }"""
        )
        oversized = page.evaluate(
            """async () => {
              const drafts = window.ItineraryVisualEditor.require('drafts');
              drafts.persist();
              await drafts.flush();
              const storage = window.ItineraryVisualEditor.require('draftStorage');
              return {paused: storage.isPaused(), reason: storage.pauseReason()};
            }"""
        )
        assert oversized == {"paused": True, "reason": "size"}

        page.locator('[data-edit-key="days.0.title"]').evaluate(
            """element => {
              element.textContent = 'Smaller visual draft';
              element.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
            }"""
        )
        recovered = page.evaluate(
            """async () => {
              const drafts = window.ItineraryVisualEditor.require('drafts');
              drafts.persist();
              await drafts.flush();
              const storage = window.ItineraryVisualEditor.require('draftStorage');
              return {
                paused: storage.isPaused(),
                reason: storage.pauseReason(),
                raw: drafts.read(),
                detail: document.getElementById('saveStatusDetail')?.textContent || '',
              };
            }"""
        )
        assert recovered["paused"] is False
        assert recovered["reason"] == ""
        assert "Smaller visual draft" in recovered["raw"]
        assert "Browser recovery paused" not in recovered["detail"]
        assert "Browser recovery draft is saved locally" in recovered["detail"]

        page.locator('[data-edit-key="days.0.title"]').evaluate(
            """element => {
              element.textContent = 'y'.repeat(50000);
              element.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
            }"""
        )
        page.evaluate(
            """async () => {
              const drafts = window.ItineraryVisualEditor.require('drafts');
              drafts.persist();
              await drafts.flush();
            }"""
        )
        assert page.evaluate("window.ItineraryVisualEditor.require('draftStorage').pauseReason()") == "size"

        next_payload = visual_editor_payload()
        next_payload["draft_id"] = "visual-editor-normal-size"
        next_payload["meta"]["source_signature"] = "visual-editor-normal-size-signature"
        result = page.evaluate(
            """async (payload) => {
              const storage = window.ItineraryVisualEditor.require('draftStorage');
              await storage.prepare(payload);
              const raw = JSON.stringify({saved_at: Date.now(), model: {title: 'Normal project draft'}});
              const queued = storage.write(raw);
              await storage.flush();
              return {
                queued,
                paused: storage.isPaused(),
                reason: storage.pauseReason(),
                raw: storage.read(),
              };
            }""",
            next_payload,
        )
        assert result["queued"] is True
        assert result["paused"] is False
        assert result["reason"] == ""
        assert "Normal project draft" in result["raw"]
    finally:
        browser.close()
        manager.stop()


def test_visual_editor_clean_render_writes_only_after_the_first_edit() -> None:
    manager, browser, page, _payload = open_visual_editor_browser_page()
    try:
        assert page.evaluate("Number(window.__fakeIndexedDbPutCount || 0)") == 0
        page.locator('[data-edit-key="days.0.title"]').evaluate(
            """element => {
              element.textContent = 'First visual edit';
              element.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
            }"""
        )
        result = page.evaluate(
            """async () => {
              const drafts = window.ItineraryVisualEditor.require('drafts');
              drafts.persist();
              await drafts.flush();
              return {
                puts: Number(window.__fakeIndexedDbPutCount || 0),
                raw: drafts.read(),
              };
            }"""
        )
        assert result["puts"] == 1
        assert "First visual edit" in result["raw"]
    finally:
        browser.close()
        manager.stop()
