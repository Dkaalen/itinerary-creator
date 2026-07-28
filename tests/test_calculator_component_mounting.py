from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text


FRONTEND_DIR = Path("calculator_grid_component/frontend")


def _calculator_js_bundle_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted((FRONTEND_DIR / "js").glob("calculator_grid_*.js")))


def test_calculator_component_registers_message_listener_before_ready_signal() -> None:
    app_source = read_contract_text(FRONTEND_DIR / "js/calculator_grid_app.js")
    bridge_source = read_contract_text(FRONTEND_DIR / "js/streamlit_bridge.js")

    assert "Streamlit.setComponentReady();" not in bridge_source
    assert "window.addEventListener('message', handleStreamlitRender);" in app_source
    assert app_source.index("window.addEventListener('message', handleStreamlitRender);") < app_source.index("Streamlit.setComponentReady();")


def test_calculator_component_has_visible_loading_and_error_states() -> None:
    bridge_source = read_contract_text(FRONTEND_DIR / "js/streamlit_bridge.js")
    app_source = read_contract_text(FRONTEND_DIR / "js/calculator_grid_app.js")
    css_source = read_contract_text(FRONTEND_DIR / "styles/calculator_grid.css")

    assert "renderComponentBootMessage" in bridge_source
    assert "Waiting for calculator data from Streamlit" in app_source
    assert ".component-loading" in css_source
    assert "Calculator grid failed to render" in app_source


def test_calculator_component_index_references_existing_assets() -> None:
    index_source = read_contract_text(FRONTEND_DIR / "index.html")
    for marker in ('href="', 'src="'):
        parts = index_source.split(marker)[1:]
        for part in parts:
            relative = part.split('"', 1)[0]
            assert (FRONTEND_DIR / relative).exists(), relative


def test_calculator_component_installs_global_frontend_diagnostics() -> None:
    index_source = read_contract_text(FRONTEND_DIR / "index.html")
    diagnostics_source = read_contract_text(FRONTEND_DIR / "js/calculator_grid_diagnostics.js")
    bridge_source = read_contract_text(FRONTEND_DIR / "js/streamlit_bridge.js")
    css_source = read_contract_text(FRONTEND_DIR / "styles/calculator_grid.css")

    assert "js/calculator_grid_diagnostics.js" in index_source
    assert index_source.index("js/streamlit_bridge.js") < index_source.index("js/calculator_grid_diagnostics.js")
    assert "window.addEventListener('error'" in diagnostics_source
    assert "window.addEventListener('unhandledrejection'" in diagnostics_source
    assert "renderCalculatorFrontendError" in bridge_source
    assert "Calculator grid frontend error" in bridge_source
    assert "escapeCalculatorErrorHtml" in bridge_source
    assert "${escapeCalculatorErrorHtml(details)}" in bridge_source
    error_renderer = bridge_source.split("function renderCalculatorFrontendError", maxsplit=1)[1]
    assert "${escapeHtml" not in error_renderer
    assert "overflow-wrap: anywhere" in css_source


def test_calculator_component_preserves_browser_draft_on_same_backend_revision() -> None:
    source = _calculator_js_bundle_source()

    assert "activeBackendRevision" in source
    assert "hasLocalDraft" in source
    assert "shouldKeepBrowserDraft(incomingRevision, incomingDraftStorageKey)" in source
    assert "mergeBackendPayloadWithoutRows(payload, incomingRevision);" in source
    assert "markLocalDraft();" in source
    assert "client_state_revision: activeBackendRevision" in source


def test_calculator_component_persists_browser_draft_across_page_changes() -> None:
    source = _calculator_js_bundle_source()
    index_source = read_contract_text(FRONTEND_DIR / "index.html")

    assert "js/calculator_grid_storage_api.js" in index_source
    assert "initializeStorage" in source
    assert "writeDraftRaw" in source
    assert "window.localStorage.setItem" not in source
    assert "window.ItineraryCalculator.storage.setDraftStorageKey(payload.draft_storage_key)" in source
    assert "window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);" in source
    assert "activeDraftStorageKey" in source
    assert "incomingDraftStorageKey === activeDraftStorageKey" in source
    assert "window.ItineraryCalculator.storage.loadDraft()" in source
    assert "window.ItineraryCalculator.storage.shouldRestoreDraft(storedDraft, incomingRows, incomingRevision)" in source
    assert "flushCalculatorRecoveryForPageExit" in source
    assert "window.addEventListener('pagehide', flushCalculatorRecoveryForPageExit)" in source


def test_component_bridge_queues_session_messages_until_first_render() -> None:
    bridge_source = read_contract_text(FRONTEND_DIR / "js/streamlit_bridge.js")
    app_source = read_contract_text(FRONTEND_DIR / "js/calculator_grid_app.js")

    assert "streamlitBridgeRenderReceived = false" in bridge_source
    assert "requiresRender && !streamlitBridgeRenderReceived" in bridge_source
    assert "pendingStreamlitFrameHeight" in bridge_source
    assert "markStreamlitRenderReceived();" in app_source
    assert "pagehide" in bridge_source
    assert "beforeunload" in bridge_source


def test_streamlit_dependency_includes_session_info_race_fix() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "streamlit==1.45.1" in requirements


def test_calculator_component_uses_revision_safe_request_ack_protocol() -> None:
    index_source = read_contract_text(FRONTEND_DIR / "index.html")
    protocol_source = read_contract_text(FRONTEND_DIR / "js/calculator_grid_protocol.js")
    controller_source = read_contract_text(FRONTEND_DIR / "js/calculator_grid_state_controller.js")
    submission_source = read_contract_text(FRONTEND_DIR / "js/calculator_grid_submission_actions.js")
    excel_source = read_contract_text(FRONTEND_DIR / "js/calculator_grid_excel_actions.js")

    assert "js/calculator_grid_protocol.js" in index_source
    assert "beginCalculatorRequest" in protocol_source
    assert "consumeCalculatorComponentAck" in protocol_source
    assert "request_id: requestId" in submission_source
    assert "client_state_revision: activeBackendRevision" in submission_source
    assert "project_identity: activeProjectIdentity" in submission_source
    assert "request_id: requestId" in excel_source
    assert "component_ack" in controller_source
    assert "canRebaseNewerEdits" in controller_source
    assert "calculatorState.dirty = false" not in submission_source
