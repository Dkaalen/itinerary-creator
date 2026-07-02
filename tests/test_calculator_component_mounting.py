from __future__ import annotations

from pathlib import Path


FRONTEND_DIR = Path("calculator_grid_component/frontend")


def test_calculator_component_registers_message_listener_before_ready_signal() -> None:
    app_source = (FRONTEND_DIR / "js/calculator_grid_app.js").read_text(encoding="utf-8")
    bridge_source = (FRONTEND_DIR / "js/streamlit_bridge.js").read_text(encoding="utf-8")

    assert "Streamlit.setComponentReady();" not in bridge_source
    assert "window.addEventListener('message', handleStreamlitRender);" in app_source
    assert app_source.index("window.addEventListener('message', handleStreamlitRender);") < app_source.index("Streamlit.setComponentReady();")


def test_calculator_component_has_visible_loading_and_error_states() -> None:
    bridge_source = (FRONTEND_DIR / "js/streamlit_bridge.js").read_text(encoding="utf-8")
    app_source = (FRONTEND_DIR / "js/calculator_grid_app.js").read_text(encoding="utf-8")
    css_source = (FRONTEND_DIR / "styles/calculator_grid.css").read_text(encoding="utf-8")

    assert "renderComponentBootMessage" in bridge_source
    assert "Waiting for calculator data from Streamlit" in app_source
    assert ".component-loading" in css_source
    assert "Calculator grid failed to render" in app_source


def test_calculator_component_index_references_existing_assets() -> None:
    index_source = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    for marker in ('href="', 'src="'):
        parts = index_source.split(marker)[1:]
        for part in parts:
            relative = part.split('"', 1)[0]
            assert (FRONTEND_DIR / relative).exists(), relative


def test_calculator_component_installs_global_frontend_diagnostics() -> None:
    index_source = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    diagnostics_source = (FRONTEND_DIR / "js/calculator_grid_diagnostics.js").read_text(encoding="utf-8")
    bridge_source = (FRONTEND_DIR / "js/streamlit_bridge.js").read_text(encoding="utf-8")
    css_source = (FRONTEND_DIR / "styles/calculator_grid.css").read_text(encoding="utf-8")

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
    app_source = (FRONTEND_DIR / "js/calculator_grid_app.js").read_text(encoding="utf-8")

    assert "activeBackendRevision" in app_source
    assert "hasLocalDraft" in app_source
    assert "shouldKeepBrowserDraft(incomingRevision)" in app_source
    assert "mergeBackendPayloadWithoutRows(payload, incomingRevision);" in app_source
    assert "markLocalDraft();" in app_source
    assert "client_state_revision: activeBackendRevision" in app_source
