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


def test_workflow_cards_keep_readable_contrast(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert "--surface-glass: #ffffff;" in css
    assert "--ink-soft: #344054;" in css
    assert ".workflow-step-locked {" in css
    assert "opacity: 1;" in css
    assert "background: var(--locked-soft);" in css
    assert "color: var(--ink-soft);" in css


def test_sidebar_controls_have_explicit_light_inputs_and_dark_text(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert 'div[data-testid="stSidebar"] [data-baseweb="select"] > div' in css
    assert "background: #f8fafc !important;" in css
    assert "color: #102033 !important;" in css
    assert 'div[data-testid="stSidebar"] .stButton > button' in css
    assert "color: #ffffff !important;" in css


def test_text_inputs_and_placeholders_are_not_low_contrast(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert 'div[data-testid="stTextArea"] textarea::placeholder' in css
    assert "color: #667085 !important;" in css
    assert "opacity: 1 !important;" in css
    assert "box-shadow: 0 0 0 3px rgba(0, 127, 121, 0.18) !important;" in css
