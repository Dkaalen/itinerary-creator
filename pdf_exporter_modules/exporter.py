from pathlib import Path
import tempfile

from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

from .renderers import render_cover_page, render_general_page, render_glance_page
from .styles import (
    apply_pdf_palette,
    extract_pdf_palette,
    make_styles,
    page_background,
    standardize_day_typography,
)


def export_html_to_pdf(html_path, pdf_path):
    """
    Converts the generated itinerary HTML into an A4 PDF without browser dependencies.
    """

    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    apply_pdf_palette(extract_pdf_palette(soup))
    pages = soup.select(".a4-page")

    styles = standardize_day_typography(make_styles())
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=24 * mm,
        bottomMargin=22 * mm,
        title="Itinerary Preview",
        author="Itinerary Creator",
    )
    doc.allowSplitting = 1

    story = []

    with tempfile.TemporaryDirectory(prefix="itinerary_day_images_") as image_temp_dir:
        for index, page in enumerate(pages):
            classes = page.get("class") or []

            if "cover-page" in classes:
                render_cover_page(page, story, styles)
            elif page.select_one(".glance-card") or page.select_one(".journey-arc"):
                render_glance_page(page, story, styles)
            else:
                render_general_page(
                    page,
                    story,
                    styles,
                    html_path=html_path,
                    temp_dir=image_temp_dir,
                    available_width=doc.width,
                    available_height=doc.height,
                    left_margin=doc.leftMargin,
                    top_margin=doc.topMargin,
                )

            if index < len(pages) - 1:
                story.append(PageBreak())

        if not story:
            story.append(Paragraph("Itinerary preview", styles["page_title"]))

        doc.build(story, onFirstPage=page_background, onLaterPages=page_background)

    return pdf_path
