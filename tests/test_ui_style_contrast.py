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


def test_primary_buttons_use_quiet_taupe_not_green_or_black(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert "[data-testid=\"stBaseButton-primary\"]" in css
    assert "background: var(--primary-action) !important;" in css
    assert "color: var(--primary-action-text) !important;" in css
    assert "background: linear-gradient(180deg, var(--teal) 0%, var(--teal-dark) 100%) !important;" not in css
    assert "background: linear-gradient(180deg, var(--sumi-2) 0%, var(--action) 100%) !important;" not in css
    assert "#0f6a5f" not in css
    assert "#094f47" not in css


def test_text_inputs_and_placeholders_are_not_low_contrast(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert 'div[data-testid="stTextArea"] textarea::placeholder' in css
    assert "color: #85827a !important;" in css
    assert "opacity: 1 !important;" in css
    assert "box-shadow: 0 0 0 3px rgba(168, 153, 134, 0.15), inset 0 1px 0 rgba(255,255,255,.72) !important;" in css


def test_legacy_header_status_and_step_grid_stay_removed(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert ".luxury-hero," in css
    assert ".compact-app-header," in css
    assert ".hero-summary-card," in css
    assert ".flow-nav," in css
    assert ".document-stage-panel," in css
    assert "display: none !important;" in css
    assert "max-width: min(100% - 3rem, 1480px)" in css
    assert ".workflow-step-grid { display: none; }" not in css
    assert "data-testid=\"stSidebar\"" not in css


def test_product_workspace_palette_uses_quiet_luxury_tokens(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert "--app-bg: #f8f6f1;" in css
    assert "--paper: #fffdf8;" in css
    assert "--ink: #1f2630;" in css
    assert "--accent: #9a8f7f;" in css
    assert "--primary-action: #233446;" in css
    assert "--teal: var(--accent);" in css
    assert "--red: #ef3a5d;" in css
    assert "[data-testid=\"stFileUploaderDropzone\"]" in css
    assert "background: rgba(255, 253, 248, 0.74) !important;" in css


def test_open_project_calculator_and_local_library_surfaces_keep_readable_contrast(monkeypatch):
    css = _rendered_css(monkeypatch)

    assert '.block-container:has(.open-project-workspace) div[data-testid="stTextInput"] input' in css
    assert '.block-container:has(.open-project-workspace) .cloud-project-card strong' in css
    assert 'color: #1f2630 !important;' in css
    assert 'color: #fffdf8 !important;' in css
    assert '.block-container:has(.calculator-heading) [data-testid="stExpander"]' in css
    assert '.block-container:has(.local-library-heading) [data-testid="stExpander"]' in css
    assert '.block-container:has(.calculator-heading) iframe[title="calculator_grid"]' in css
