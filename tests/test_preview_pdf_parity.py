import re
import sys
import tempfile
import types
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")

    class _SessionState(dict):
        def __getattr__(self, name):
            return self.get(name)

    streamlit_stub.session_state = _SessionState()
    streamlit_stub.error = lambda *args, **kwargs: None
    streamlit_stub.exception = lambda *args, **kwargs: None
    sys.modules["streamlit"] = streamlit_stub

from app_modules.itinerary_html import build_itinerary_html
from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from pdf_exporter import export_html_to_pdf
from tests.rendered_pdf_quality import _lighten_html_for_pdf_quality, compact_text, normalize_text


def _pdf_text_from_html(html: str) -> str:
    try:
        import fitz
    except Exception as exc:  # pragma: no cover - dependency guard
        raise AssertionError(f"PyMuPDF/fitz is required for preview/PDF parity checks: {exc}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_path = tmp_path / "preview.html"
        pdf_path = tmp_path / "preview.pdf"
        html_path.write_text(_lighten_html_for_pdf_quality(html), encoding="utf-8")
        export_html_to_pdf(html_path, pdf_path)
        document = fitz.open(pdf_path)
        try:
            return normalize_text("\n".join(page.get_text("text") for page in document))
        finally:
            document.close()


def _build_fixture_html(fixture_name: str) -> str:
    raw = (ROOT / "tests" / "fixtures" / "real_inputs" / fixture_name).read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    import ui.day_pages as day_pages

    day_pages.select_day_images_with_overrides = lambda grouped_days, output_edits=None: {}
    day_pages.render_day_image_slot = lambda *args, **kwargs: ""
    return """<!DOCTYPE html>
<html><head><meta charset=\"UTF-8\"><title>Preview</title></head><body>""" + build_itinerary_html(rows, grouped, output_edits={}) + "</body></html>"


def _preview_visible_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    for hidden in soup.select("style, script, .day-label-legacy, .day-image-slot, .day-visual-block"):
        hidden.decompose()

    for route in soup.select(".cover-destinations"):
        route.string = route.get_text(" ").upper()

    text = normalize_text("\n".join(page.get_text("\n") for page in soup.select(".a4-page")))
    lines = []
    for line in text.split("\n"):
        cleaned = compact_text(line)
        if len(cleaned) > 2:
            lines.append(cleaned)
    return lines


def test_pdf_exporter_uses_preview_text_without_pdf_side_time_rewrites():
    html = """
    <html><body>
      <div class="a4-page day-page single-day-page">
        <section class="day-section">
          <div class="day-kicker">DAY 1 ✦ OSLO ✦ 1st of January</div>
          <div class="day-title">Guided Walk</div>
          <div class="intro">A calm city introduction.</div>
          <div class="content-block activity-block">
            <div class="section-title">Morning Experience</div>
            <div class="body-text strong-line">Guided Walk</div>
            <div class="body-text"><span class="meta-label">Time:</span> 10:00 AM</div>
            <div class="body-text"><span class="meta-label">Duration:</span> 2 hours</div>
          </div>
        </section>
      </div>
    </body></html>
    """
    pdf_text = compact_text(_pdf_text_from_html(html))
    assert "Time: 10:00 AM" in pdf_text
    assert "Time: 10:00 AM - 12:00 PM" not in pdf_text


def test_preview_visible_text_is_present_in_rendered_pdf_for_real_fixture():
    html = _build_fixture_html("norway_short_oslo_bergen_alesund.txt")
    pdf_text = compact_text(_pdf_text_from_html(html))

    missing = [line for line in _preview_visible_lines(html) if line not in pdf_text]
    assert not missing, "Rendered PDF is missing preview-visible text:\n" + "\n".join(missing[:20])
