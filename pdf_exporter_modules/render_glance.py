"""Trip-at-a-glance PDF rendering."""

from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer

from . import styles as pdf_styles
from .html_utils import clean_text, para_text
from .image_flowables import FullPageBackgroundImage, FullPageTint
from .pdf_branding import is_booknordics_pdf
from .image_paths import resolve_image_path
from .render_flowables import boxed_story_table
from .story import add_paragraph, make_table


def add_soft_summary_background(page, story, html_path=None, temp_dir=None):
    """Add the seasonal artwork softly behind the summary page cards."""
    background_path = resolve_image_path(page.get("data-cover-background-path"), html_path) if html_path else None
    if background_path and temp_dir:
        story.append(FullPageBackgroundImage(background_path, temp_dir, crop_focus="top"))
        story.append(FullPageTint(color=pdf_styles.PAGE_BACKGROUND, alpha=0.58 if is_booknordics_pdf() else 0.38))


def render_glance_page(page, story, styles, html_path=None, temp_dir=None):
    add_soft_summary_background(page, story, html_path=html_path, temp_dir=temp_dir)

    glance_story = []
    title = page.select_one(".glance-title")
    add_paragraph(glance_story, title.get_text(" ") if title else "Your Trip at a Glance", styles["summary_title"], spacer_after=5)

    rows = []
    for row in page.select(".glance-row"):
        label = row.select_one(".glance-label")
        value = row.select_one(".glance-value")
        if label and value:
            rows.append([
                Paragraph(para_text(label.get_text(" ")), styles["summary_header"]),
                Paragraph(para_text(value.get_text(" ")), styles["summary_cell"]),
            ])

    if rows:
        glance_story.append(make_table(rows, [34 * mm, 104 * mm], styles))

    story.append(boxed_story_table(glance_story, background=pdf_styles.SUMMARY_CARD))
    story.append(Spacer(1, 12 * mm))

    journey_story = []
    journey_title = page.select_one(".journey-title")
    add_paragraph(journey_story, journey_title.get_text(" ") if journey_title else "How Your Trip Unfolds", styles["summary_title"], spacer_after=5)

    table_rows = []
    header_cells = [clean_text(th.get_text(" ")) for th in page.select(".journey-table th")]
    if header_cells:
        table_rows.append([Paragraph(para_text(cell), styles["summary_header"]) for cell in header_cells])

    for tr in page.select(".journey-table tbody tr"):
        cells = [clean_text(td.get_text(" ")) for td in tr.select("td")]
        if cells:
            table_rows.append([Paragraph(para_text(cell), styles["summary_cell"]) for cell in cells])

    if table_rows:
        journey_story.append(make_table(table_rows, [34 * mm, 16 * mm, 90 * mm], styles))

    story.append(boxed_story_table(journey_story, background=pdf_styles.SUMMARY_CARD))
