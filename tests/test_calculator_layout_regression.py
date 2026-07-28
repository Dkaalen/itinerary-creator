from __future__ import annotations

from ui import style_calculator
from tests.support.streamlit_stub import install_streamlit_stub


def test_calculator_component_host_keeps_full_width_contract() -> None:
    css = style_calculator.CALCULATOR_PAGE_CSS

    assert '.block-container:has(.calculator-heading)' in css
    assert 'min-width: 0 !important;' in css
    assert 'min-width: min(100%, 980px) !important;' not in css
    assert 'iframe' in css
    assert 'width: 100% !important;' in css
    assert 'width: auto !important;' not in css.split('div[data-testid="stCustomComponentV1"]', 1)[-1].split('@media', 1)[0]


def test_calculator_page_renders_css_from_ui_style_layer(monkeypatch) -> None:
    install_streamlit_stub(force=True)
    from app_modules import calculator_page

    rendered: list[str] = []

    def fake_markdown(body: str, **kwargs: object) -> None:
        rendered.append(body)
        assert kwargs == {"unsafe_allow_html": True}

    monkeypatch.setattr(calculator_page.st, "markdown", fake_markdown)

    calculator_page._render_calculator_page_css()

    assert rendered == [f"<style>{style_calculator.CALCULATOR_PAGE_CSS}</style>"]
