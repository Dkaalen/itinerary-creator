import importlib
import sys
from types import SimpleNamespace


def _styles_module(monkeypatch):
    fake_streamlit = SimpleNamespace(markdown=lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    sys.modules.pop("ui.styles", None)
    return importlib.import_module("ui.styles")


def _rendered_css(monkeypatch):
    styles = _styles_module(monkeypatch)
    captured = {}

    def fake_markdown(body, unsafe_allow_html=False):
        captured["body"] = body
        captured["unsafe_allow_html"] = unsafe_allow_html

    monkeypatch.setattr(styles.st, "markdown", fake_markdown)
    styles.apply_global_styles()
    assert captured["unsafe_allow_html"] is True
    return captured["body"]


def test_primary_buttons_are_explicitly_high_contrast(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert "[data-testid=\"stBaseButton-primary\"]" in css
    assert "background: var(--teal-dark) !important;" in css
    assert "color: #ffffff !important;" in css


def test_text_inputs_and_placeholders_are_not_low_contrast(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert 'div[data-testid="stTextArea"] textarea::placeholder' in css
    assert "color: #6f7f8e !important;" in css
    assert "opacity: 1 !important;" in css
    assert "box-shadow: 0 0 0 3px rgba(13, 111, 104, 0.13) !important;" in css


def test_legacy_header_status_and_step_grid_stay_removed(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert ".luxury-hero," in css
    assert ".compact-app-header," in css
    assert ".hero-summary-card," in css
    assert ".flow-nav," in css
    assert ".document-stage-panel," in css
    assert "display: none !important;" in css
    assert "max-width: min(100% - 2.2rem, 1880px)" in css
    assert ".workflow-step-grid { display: none; }" not in css
    assert "data-testid=\"stSidebar\"" not in css


def test_product_workspace_palette_uses_quiet_luxury_tokens(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert "--app-bg: #f7f3ec;" in css
    assert "--paper: #fffdfa;" in css
    assert "--ink: #0e2337;" in css
    assert "--teal: #0d6f68;" in css
    assert "--red: #d94b5f;" in css
    assert "[data-testid=\"stFileUploaderDropzone\"]" in css
    assert "background: rgba(255, 253, 250, 0.95) !important;" in css
