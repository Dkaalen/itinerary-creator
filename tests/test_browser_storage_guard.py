from __future__ import annotations

import sys
import types

from app_modules import browser_storage_guard
from app_modules.browser_storage_contract import browser_storage_contract


def test_browser_storage_guard_uses_authoritative_contract_and_preserves_unrelated_keys() -> None:
    script = browser_storage_guard._BROWSER_STORAGE_GUARD
    contract = browser_storage_contract()

    assert contract["owners"]["calculator"]["current_prefix"] in script
    assert contract["owners"]["visual_editor"]["current_prefix"] in script
    assert contract["owners"]["visual_editor"]["legacy_prefixes"][0] in script
    assert contract["indexed_db"]["name"] in script
    assert contract["cleanup_session_key"] in script
    assert "window.parent.localStorage" in script
    assert "window.parent.indexedDB" in script
    assert "window.localStorage" not in script
    assert "localStorage.clear" not in script
    assert "No completion marker is written" in script


def test_browser_storage_guard_mounts_idempotent_browser_script_on_each_rerun(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_html(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    streamlit_module = types.ModuleType("streamlit")
    components_module = types.ModuleType("streamlit.components")
    v1_module = types.ModuleType("streamlit.components.v1")
    v1_module.html = fake_html
    components_module.v1 = v1_module
    streamlit_module.components = components_module
    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.components", components_module)
    monkeypatch.setitem(sys.modules, "streamlit.components.v1", v1_module)
    state: dict = {}

    browser_storage_guard.render_browser_storage_guard(state)
    browser_storage_guard.render_browser_storage_guard(state)

    assert len(calls) == 2
    assert all(call["kwargs"] == {"height": 0, "width": 0} for call in calls)
    assert not any(str(key).startswith("browser_storage_guard_rendered") for key in state)


def test_browser_storage_contract_is_isolated_and_matches_production_key_owners() -> None:
    from app_modules.calculator_component_payload import _draft_storage_key

    first = browser_storage_contract()
    second = browser_storage_contract()
    first["owners"]["calculator"]["legacy_prefixes"].append("mutated.")

    assert "mutated." not in second["owners"]["calculator"]["legacy_prefixes"]
    assert _draft_storage_key("project:abc").startswith(second["owners"]["calculator"]["current_prefix"])
    assert second["owners"]["visual_editor"]["current_prefix"] == "itinerary-visual-editor-draft:"
    assert "itineraryVisualEditorDraft." in second["owners"]["visual_editor"]["legacy_prefixes"]
