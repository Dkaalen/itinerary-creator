from reportlab.platypus import Paragraph

from pdf_exporter_modules.render_glance import render_glance_page
from pdf_exporter_modules.story import make_table
from pdf_exporter_modules.styles import make_styles


def test_pdf_summary_uses_proposal_title_style():
    styles = make_styles()

    assert "summary_title" in styles
    assert styles["summary_title"].fontSize < styles["page_title"].fontSize
    assert styles["summary_title"].fontName == "Times-Bold"
    assert styles["summary_cell"].fontName == "Times-Roman"


def test_pdf_summary_table_avoids_spreadsheet_grid():
    styles = make_styles()
    table = make_table(
        [[Paragraph("Duration", styles["summary_header"]), Paragraph("8 days", styles["summary_cell"])]],
        [50, 100],
        styles,
    )

    line_commands = [command[0] for command in getattr(table, "_linecmds", [])]
    background_commands = [command[0] for command in getattr(table, "_bkgrndcmds", [])]

    assert "LINEBELOW" in line_commands
    assert "INNERGRID" not in line_commands
    assert "BOX" not in line_commands
    assert "BACKGROUND" not in background_commands


def test_html_summary_renderer_uses_luxury_summary_styles(monkeypatch):
    from bs4 import BeautifulSoup

    captured_style_names = []

    def fake_add_paragraph(story, text, style, *args, **kwargs):
        captured_style_names.append(style.name)
        story.append((text, style.name))

    monkeypatch.setattr("pdf_exporter_modules.render_glance.add_paragraph", fake_add_paragraph)
    page = BeautifulSoup(
        """
        <div class="a4-page summary-page">
          <div class="glance-card">
            <div class="glance-title">Your Trip at a Glance</div>
            <div class="glance-row"><div class="glance-label">Duration</div><div class="glance-value">8 days</div></div>
          </div>
          <div class="journey-arc">
            <div class="journey-title">Your Journey Arc</div>
            <table class="journey-table"><tbody><tr><td>Oslo</td><td>1-2</td><td>Arrival</td></tr></tbody></table>
          </div>
        </div>
        """,
        "html.parser",
    ).select_one(".summary-page")

    render_glance_page(page, [], make_styles())

    assert captured_style_names.count("summary_title") == 2
    assert "page_title" not in captured_style_names
