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
