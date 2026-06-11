from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from itinerary_generation.render_model import RenderBlock, RenderDay, RenderDocument, RenderMetaLine
from pdf_exporter import export_html_to_pdf, export_render_document_to_pdf
from pdf_exporter_modules.day_page_guard import PdfDayLayoutError


def _page_texts(pdf_path: Path) -> list[str]:
    try:
        import fitz
    except Exception as exc:  # pragma: no cover - dependency guard
        raise AssertionError(f"PyMuPDF/fitz is required for PDF page ownership checks: {exc}")

    document = fitz.open(pdf_path)
    try:
        return [page.get_text("text") for page in document]
    finally:
        document.close()


def test_typed_pdf_keeps_day_heading_and_activity_on_same_page():
    day = RenderDay(
        day="4",
        number="4",
        city="Rovaniemi",
        date="13th of February",
        title="Northern Lights Hunt",
        intro="The day is kept easy around your evening Northern Lights experience, giving you time to settle before heading out with local guidance after dark.",
        blocks=[
            RenderBlock(
                kind="transport",
                section_title="Travel Arrangements",
                lines=["Private transfer from Rovaniemi Railway Station to your accommodation"],
            ),
            RenderBlock(
                kind="accommodation",
                section_title="Accommodation",
                title="Scandic Polar in Rovaniemi for 2 nights",
                lines=["Room category: 1 x Standard Double Room, breakfast included"],
            ),
            RenderBlock(
                kind="activity",
                section_title="Evening Experience",
                title="Northern Lights Hunt by Minibus at the Arctic Circle",
                meta=[
                    RenderMetaLine("Time", "8:00 PM - 11:00 PM"),
                    RenderMetaLine("Duration", "3 hours"),
                    RenderMetaLine("Meeting point", "Arctic City Snowmobile Park office, Koskikatu 8, Rovaniemi"),
                ],
                includes=[
                    "Pick-up/drop-off in central Rovaniemi",
                    "Professional, English-speaking guide",
                    "Winter overalls, boots and gloves",
                    "Warm juice and cookies",
                ],
                description="Head out in search of the Northern Lights in Rovaniemi, with the route adapted to the evening conditions and local guidance included.",
            ),
        ],
    )
    document = RenderDocument(title="Lapland Winter", route="Rovaniemi", days=[day])

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "typed.pdf"
        export_render_document_to_pdf(document, pdf_path)
        pages = _page_texts(pdf_path)

    assert len(pages) == 2
    day_page = pages[1]
    assert "DAY 4" in day_page
    assert "Northern Lights Hunt by Minibus" in day_page
    assert "Scandic Polar" in day_page


def test_legacy_html_pdf_keeps_day_page_atomic_after_activity_blocks():
    html = """
    <html><body>
      <div class="a4-page cover-page"><div class="cover-title">Lapland Winter</div></div>
      <div class="a4-page day-page single-day-page" id="day-4">
        <section class="day-section">
          <div class="day-kicker">DAY 4 ✦ ROVANIEMI ✦ 13th of February</div>
          <div class="day-title">Northern Lights Hunt</div>
          <div class="intro">The day is kept easy around your evening Northern Lights experience, giving you time to settle before heading out with local guidance after dark.</div>
          <div class="content-block">
            <div class="section-title">Travel Arrangements</div>
            <ul><li>Private transfer from Rovaniemi Railway Station to your accommodation</li></ul>
          </div>
          <div class="content-block">
            <div class="section-title">Accommodation</div>
            <div class="body-text strong-line">Scandic Polar in Rovaniemi for 2 nights</div>
            <div class="body-text">Room category: 1 x Standard Double Room, breakfast included</div>
          </div>
          <div class="content-block activity-block">
            <div class="section-title">Evening Experience</div>
            <div class="activity-inclusion-title">Northern Lights Hunt by Minibus at the Arctic Circle</div>
            <div class="body-text">Time: 8:00 PM - 11:00 PM</div>
            <div class="body-text">Duration: 3 hours</div>
            <div class="body-text">Meeting point: Arctic City Snowmobile Park office, Koskikatu 8, Rovaniemi</div>
            <div class="section-title">Included With This Experience</div>
            <ul>
              <li>Pick-up/drop-off in central Rovaniemi</li>
              <li>Professional, English-speaking guide</li>
              <li>Winter overalls, boots and gloves</li>
              <li>Warm juice and cookies</li>
            </ul>
            <div class="section-title">Description</div>
            <div class="body-text">Head out in search of the Northern Lights in Rovaniemi, with the route adapted to the evening conditions and local guidance included.</div>
          </div>
        </section>
      </div>
    </body></html>
    """

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_path = tmp_path / "preview.html"
        pdf_path = tmp_path / "preview.pdf"
        html_path.write_text(html, encoding="utf-8")
        export_html_to_pdf(html_path, pdf_path)
        pages = _page_texts(pdf_path)

    assert len(pages) == 2
    assert "DAY 4" in pages[1]
    assert "Northern Lights Hunt by Minibus" in pages[1]
    assert all(not page.strip().startswith("Evening Experience") for page in pages)


def test_legacy_html_pdf_blocks_impossible_day_split():
    long_lines = "".join(f'<div class="body-text">Long detail line {i}: {'very detailed supplier text ' * 8}</div>' for i in range(80))
    html = f"""
    <html><body>
      <div class="a4-page day-page single-day-page" id="day-too-long">
        <section class="day-section">
          <div class="day-kicker">DAY 7 ✦ LAPLAND ✦ 16th of February</div>
          <div class="day-title">Arctic Explorer Icebreaker Cruise</div>
          <div class="intro">A long day with too much edited text.</div>
          <div class="content-block activity-block">{long_lines}</div>
        </section>
      </div>
    </body></html>
    """

    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "preview.html"
        pdf_path = Path(tmp) / "preview.pdf"
        html_path.write_text(html, encoding="utf-8")
        with pytest.raises(PdfDayLayoutError):
            export_html_to_pdf(html_path, pdf_path)
