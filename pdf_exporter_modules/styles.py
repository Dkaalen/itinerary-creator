import json

from bs4 import BeautifulSoup  # noqa: F401 - keeps dependency explicit for export environment
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

PAGE_BACKGROUND = colors.HexColor("#f4efe8")
INK = colors.HexColor("#1f3446")
BODY = colors.HexColor("#2f2f2f")
MUTED = colors.HexColor("#7b746c")
LINE = colors.HexColor("#d8cec2")
CARD = colors.Color(1, 1, 1, alpha=0.35)
SUMMARY_CARD = colors.Color(1, 1, 1, alpha=0.72)

DEFAULT_PDF_COLORS = {
    "page_bg": "#f4efe8",
    "ink": "#1f3446",
    "body": "#2f2f2f",
    "muted": "#7b746c",
    "line": "#d8cec2",
}


def hex_to_color(value, fallback):
    try:
        value = str(value or "").strip()
        if not value.startswith("#"):
            return fallback
        return colors.HexColor(value)
    except Exception:
        return fallback


def apply_pdf_palette(color_data):
    """Apply the selected HTML color preset to the ReportLab PDF renderer."""
    global PAGE_BACKGROUND, INK, BODY, MUTED, LINE

    color_data = color_data or {}
    PAGE_BACKGROUND = hex_to_color(color_data.get("page_bg"), PAGE_BACKGROUND)
    INK = hex_to_color(color_data.get("ink"), INK)
    BODY = hex_to_color(color_data.get("body"), BODY)
    MUTED = hex_to_color(color_data.get("muted"), MUTED)
    LINE = hex_to_color(color_data.get("line"), LINE)


def extract_pdf_palette(soup):
    wrapper = soup.select_one(".preview-background")
    if not wrapper:
        return DEFAULT_PDF_COLORS

    raw = wrapper.get("data-colors") or ""
    if not raw:
        return DEFAULT_PDF_COLORS

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {**DEFAULT_PDF_COLORS, **data}
    except Exception:
        return DEFAULT_PDF_COLORS

    return DEFAULT_PDF_COLORS


def page_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAGE_BACKGROUND)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


def make_styles():
    base = getSampleStyleSheet()

    return {
        "cover_kicker": ParagraphStyle(
            "cover_kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=12,
            textColor=MUTED,
            uppercase=True,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=38,
            leading=41,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=15.5,
            leading=20,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_route_label": ParagraphStyle(
            "cover_route_label",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_destinations": ParagraphStyle(
            "cover_destinations",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.8,
            leading=14,
            textColor=BODY,
            alignment=TA_CENTER,
            spaceBefore=0,
        ),
        "page_title": ParagraphStyle(
            "page_title",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=25,
            leading=30,
            textColor=INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=7,
        ),
        "day_label": ParagraphStyle(
            "day_label",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=25,
            leading=29,
            textColor=INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=3,
        ),
        "day_kicker": ParagraphStyle(
            "day_kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=8,
        ),
        "day_title": ParagraphStyle(
            "day_title",
            parent=base["Heading2"],
            fontName="Times-Roman",
            fontSize=20,
            leading=24,
            textColor=INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=8,
        ),
        "city": ParagraphStyle(
            "city",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
            spaceAfter=14,
        ),
        "intro": ParagraphStyle(
            "intro",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=11.5,
            leading=16,
            textColor=BODY,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=14,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=INK,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.2,
            leading=14,
            textColor=BODY,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=3,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=10.5,
            leading=14,
            textColor=BODY,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=4,
        ),
        "activity_title": ParagraphStyle(
            "activity_title",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=13.5,
            leading=17,
            textColor=INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceBefore=10,
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.0,
            leading=13,
            textColor=BODY,
            splitLongWords=0,
            wordWrap="LTR",
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=0,
        ),
        "bullet_continuation": ParagraphStyle(
            "bullet_continuation",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.0,
            leading=13,
            textColor=MUTED,
            splitLongWords=0,
            wordWrap="LTR",
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=0,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=INK,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.6,
            leading=11.6,
            textColor=BODY,
            splitLongWords=0,
            wordWrap="LTR",
        ),
    }
