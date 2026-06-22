from bs4 import BeautifulSoup

from itinerary_generation.render_model import RenderCover, RenderDocument
from pdf_exporter_modules import cover_page
from pdf_exporter_modules.render_cover import render_cover_page
from pdf_exporter_modules.styles import make_styles
from pdf_exporter_modules.typed_exporter import _render_cover


def _capture_paragraphs(monkeypatch):
    captured = []

    def fake_add_paragraph(story, text, style, *args, **kwargs):
        captured.append(str(text))
        story.append(("paragraph", text))

    monkeypatch.setattr(cover_page, "add_paragraph", fake_add_paragraph)
    return captured


def test_html_cover_pdf_uses_shared_route_label_renderer(monkeypatch):
    captured = _capture_paragraphs(monkeypatch)
    soup = BeautifulSoup(
        """
        <div class="a4-page cover-page" data-cover-ink="#111111" data-cover-muted="#555555">
          <div class="cover-kicker">Travel Itinerary</div>
          <div class="cover-title">Nordic Winter</div>
          <div class="cover-subtitle">Oslo<br>Bergen</div>
          <div class="cover-dates">January 2027</div>
          <div class="cover-destination-label">Journey Map</div>
          <div class="cover-destinations">Oslo<br>Bergen</div>
        </div>
        """,
        "html.parser",
    )

    render_cover_page(soup.select_one(".cover-page"), [], make_styles(), temp_dir=None)

    assert "Journey Map" in captured
    assert "OSLO\nBERGEN" in captured


def test_typed_cover_pdf_uses_same_cover_renderer(monkeypatch):
    captured = _capture_paragraphs(monkeypatch)
    document = RenderDocument(
        title="Fallback title",
        route="Fallback route",
        cover=RenderCover(
            title="Typed Cover",
            route_label="Custom Route",
            route="Oslo\nBergen",
            ink="#111111",
            muted="#555555",
        ),
    )

    _render_cover(document, [], make_styles(), temp_dir=None)

    assert "Custom Route" in captured
    assert "OSLO · BERGEN" in captured
