from __future__ import annotations

import json
import re
from pathlib import Path

from tests.support.visual_editor_browser_harness import (
    open_bootstrapped_visual_editor_browser_page,
    open_visual_editor_browser_page,
    visual_editor_bootstrap_script_names,
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
    from tests.support.visual_editor_browser_harness import visual_editor_payload

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
            """() => {
              const key = `itinerary-visual-editor-draft:${window.ItineraryVisualEditor.require('state').snapshot().model.draft_id}`;
              return window.localStorage.getItem(key);
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
