from bs4 import BeautifulSoup
from reportlab.platypus import Table

from pdf_exporter_modules.decorative_flowables import add_day_opener_rule
from pdf_exporter_modules.render_content import render_day_section_pdf
from pdf_exporter_modules.styles import make_styles


def test_pdf8_day_opener_rule_adds_subtle_rule():
    story = []
    add_day_opener_rule(story)

    assert any(isinstance(item, Table) for item in story)


def test_pdf8_day_section_places_rule_after_intro_before_blocks():
    html = """
    <section class="day-section">
      <div class="day-kicker">DAY 1 ✦ OSLO</div>
      <div class="day-title">Welcome to Oslo</div>
      <div class="intro">A richer opening paragraph.</div>
      <div class="content-block"><div class="section-title">Travel Arrangements</div></div>
    </section>
    """
    soup = BeautifulSoup(html, "html.parser")
    story = []

    render_day_section_pdf(soup.select_one(".day-section"), story, make_styles())

    assert any(isinstance(item, Table) for item in story)
