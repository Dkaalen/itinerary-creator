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
    """Compatibility no-op: proposal footers are intentionally removed."""

    return None


def page_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(tokens.PAGE_BACKGROUND)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


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
