"""ReportLab style orchestration for PDF export."""

from __future__ import annotations

from bs4 import BeautifulSoup  # noqa: F401 - keeps dependency explicit for export environment
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

from pdf_exporter_modules import pdf_style_tokens as tokens
from pdf_exporter_modules.pdf_branding import is_booknordics_pdf, logo_path, pdf_font
from pdf_exporter_modules.pdf_style_base import make_base_styles
from pdf_exporter_modules.pdf_style_cover import make_cover_styles
from pdf_exporter_modules.pdf_style_day import make_day_styles
from pdf_exporter_modules.pdf_style_final_pages import make_final_page_styles
from pdf_exporter_modules.pdf_style_summary import make_summary_styles
from pdf_exporter_modules.pdf_style_tables import make_table_styles

_TOKEN_NAMES = {
    "PAGE_BACKGROUND",
    "INK",
    "BODY",
    "MUTED",
    "LINE",
    "ACCENT",
    "CARD",
    "SUMMARY_CARD",
    "DEFAULT_PDF_COLORS",
}


def __getattr__(name: str):
    if name in _TOKEN_NAMES:
        return getattr(tokens, name)
    raise AttributeError(name)


def hex_to_color(value, fallback):
    return tokens.hex_to_color(value, fallback)


def apply_pdf_palette(color_data):
    tokens.apply_pdf_palette(color_data)


def extract_pdf_palette(soup):
    return tokens.extract_pdf_palette(soup)


def _footer_label(doc) -> str:
    if is_booknordics_pdf():
        return "TRAVEL ITINERARY"
    title = str(getattr(doc, "title", "") or "").strip().upper()
    if title in {"", "CLIENT PDF", "COMPACT CLIENT PDF", "INTERNAL REVIEW PDF", "ITINERARY PREVIEW"}:
        return "TRAVEL ITINERARY"
    return title


def draw_proposal_footer(canvas, doc):
    """Draw a quiet proposal footer on non-cover pages."""

    if int(getattr(doc, "page", 1) or 1) <= 1:
        return

    page_width, _page_height = getattr(doc, "pagesize", A4)
    left = float(getattr(doc, "leftMargin", 22 * mm) or 22 * mm)
    right = float(page_width) - float(getattr(doc, "rightMargin", 22 * mm) or 22 * mm)
    y = max(8 * mm, float(getattr(doc, "bottomMargin", 22 * mm) or 22 * mm) * 0.42)
    rule_y = y + 5.8 * mm

    canvas.saveState()
    canvas.setStrokeColor(tokens.LINE)
    canvas.setFillColor(tokens.MUTED)
    canvas.setLineWidth(0.25)
    canvas.line(left, rule_y, right, rule_y)
    canvas.setFont(pdf_font("medium") if is_booknordics_pdf() else "Helvetica", 6.6)
    canvas.drawString(left, y, _footer_label(doc))
    canvas.drawRightString(right, y, f"{int(getattr(doc, 'page', 1) or 1):02d}")
    brand_logo = logo_path()
    if brand_logo is not None and int(getattr(doc, "page", 1) or 1) >= 3:
        canvas.drawImage(str(brand_logo), right - 36 * mm, A4[1] - 15 * mm, width=36 * mm, height=5.4 * mm, preserveAspectRatio=True, mask="auto", anchor="ne")
    canvas.restoreState()


def page_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(tokens.PAGE_BACKGROUND)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()
    draw_proposal_footer(canvas, doc)


def make_styles():
    base = getSampleStyleSheet()
    styles = {}
    for factory in (
        make_cover_styles,
        make_base_styles,
        make_day_styles,
        make_summary_styles,
        make_table_styles,
        make_final_page_styles,
    ):
        styles.update(factory(base))
    if is_booknordics_pdf():
        for style in styles.values():
            current = str(getattr(style, "fontName", "") or "")
            weight = "bold" if "Bold" in current else "regular"
            style.fontName = pdf_font(weight)
    return styles


__all__ = [
    "ACCENT",
    "BODY",
    "CARD",
    "DEFAULT_PDF_COLORS",
    "INK",
    "LINE",
    "MUTED",
    "PAGE_BACKGROUND",
    "SUMMARY_CARD",
    "apply_pdf_palette",
    "draw_proposal_footer",
    "extract_pdf_palette",
    "hex_to_color",
    "make_styles",
    "page_background",
    "_footer_label",
]
