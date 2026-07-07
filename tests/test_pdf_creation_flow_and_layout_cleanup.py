from __future__ import annotations

from types import SimpleNamespace

from app_modules.pdf_filename import pdf_filename_stem_from_state
from pdf_exporter_modules.pdf_day_renderer import render_day_story
from pdf_exporter_modules.render_pages import render_day_section_pdf
from pdf_exporter_modules.styles import draw_proposal_footer, make_styles, page_background
from itinerary_generation.render_model import RenderDay
from bs4 import BeautifulSoup


class RecordingCanvas:
    def __init__(self):
        self.calls = []

    def saveState(self): self.calls.append(("saveState",))
    def restoreState(self): self.calls.append(("restoreState",))
    def setFillColor(self, *args): self.calls.append(("setFillColor", args))
    def setStrokeColor(self, *args): self.calls.append(("setStrokeColor", args))
    def setLineWidth(self, *args): self.calls.append(("setLineWidth", args))
    def rect(self, *args, **kwargs): self.calls.append(("rect", args, kwargs))
    def line(self, *args): self.calls.append(("line", args))
    def drawString(self, *args): self.calls.append(("drawString", args))
    def drawRightString(self, *args): self.calls.append(("drawRightString", args))


def test_pdf_download_filename_uses_itinerary_name_stem() -> None:
    assert pdf_filename_stem_from_state({"itinerary_name": "  Iceland / Golden Circle  "}) == "Iceland Golden Circle"
    assert pdf_filename_stem_from_state({"itinerary_name_input": "Tromsø Northern Lights"}) == "Tromsø Northern Lights"
    assert pdf_filename_stem_from_state({}) == "Itinerary"


def test_pdf_footer_is_removed_from_background_pages() -> None:
    canvas = RecordingCanvas()

    draw_proposal_footer(canvas, SimpleNamespace(page=4, title="Luxury Proposal"))
    assert canvas.calls == []

    page_background(canvas, SimpleNamespace(page=4, title="Luxury Proposal"))
    assert any(call[0] == "rect" for call in canvas.calls)
    assert not any(call[0] in {"line", "drawString", "drawRightString"} for call in canvas.calls)


def test_typed_pdf_day_story_does_not_render_city_subtitle_under_title() -> None:
    styles = make_styles()
    day = RenderDay(day="Day 2", number="2", city="Reykjavik", title="Drysuit Snorkelling in Silfra", intro="Swim between the plates.")

    story = render_day_story(day, styles)
    rendered = [getattr(item, "text", "") for item in story]

    assert any("Drysuit Snorkelling" in text for text in rendered)
    assert "Reykjavik" not in rendered


def test_html_fallback_day_section_does_not_render_city_subtitle() -> None:
    styles = make_styles()
    section = BeautifulSoup(
        '<section class="day-section"><div class="day-title">Drysuit Snorkelling in Silfra</div><div class="city">Reykjavik</div><div class="intro">Swim.</div></section>',
        "html.parser",
    ).select_one(".day-section")
    story = []

    render_day_section_pdf(section, story, styles)
    rendered = [getattr(item, "text", "") for item in story]

    assert any("Drysuit Snorkelling" in text for text in rendered)
    assert "Reykjavik" not in rendered
