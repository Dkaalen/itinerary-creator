import json

from bs4 import BeautifulSoup  # noqa: F401 - keeps dependency explicit for export environment
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

PAGE_BACKGROUND = colors.HexColor("#f4efe8")
INK = colors.HexColor("#1f3446")
BODY = colors.HexColor("#2f2f2f")
MUTED = colors.HexColor("#7b746c")
LINE = colors.HexColor("#d8cec2")
CARD = colors.Color(1, 1, 1, alpha=0.35)

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

    # Subtle editorial corner accents. These are drawn directly into the PDF so
    # the exported file keeps the same premium frame as the HTML preview without
    # consuming any itinerary text space.
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.45)
    page_w, page_h = A4
    top = page_h - 18 * mm
    right = page_w - 18 * mm
    accent = 23 * mm
    canvas.line(right - accent, top, right, top)
    canvas.line(right, top, right, top - accent)
    canvas.line(18 * mm, 16 * mm, 46 * mm, 16 * mm)
    canvas.restoreState()


def make_styles():
    base = getSampleStyleSheet()

    return {
        "cover_kicker": ParagraphStyle(
            "cover_kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=MUTED,
            uppercase=True,
            alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=38,
            leading=42,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=17,
            leading=22,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=14,
        ),
        "cover_destinations": ParagraphStyle(
            "cover_destinations",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=BODY,
            alignment=TA_LEFT,
            spaceBefore=12,
        ),
        "page_title": ParagraphStyle(
            "page_title",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=25,
            leading=30,
            textColor=INK,
            spaceAfter=7,
        ),
        "day_label": ParagraphStyle(
            "day_label",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=25,
            leading=29,
            textColor=INK,
            spaceAfter=3,
        ),
        "day_title": ParagraphStyle(
            "day_title",
            parent=base["Heading2"],
            fontName="Times-Roman",
            fontSize=20,
            leading=24,
            textColor=INK,
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
            spaceAfter=3,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=10.5,
            leading=14,
            textColor=BODY,
            spaceAfter=4,
        ),
        "activity_title": ParagraphStyle(
            "activity_title",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=13.5,
            leading=17,
            textColor=INK,
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
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=0,
        ),
        "day_label_compact": ParagraphStyle(
            "day_label_compact",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=20,
            leading=23,
            textColor=INK,
            spaceAfter=2,
        ),
        "day_title_compact": ParagraphStyle(
            "day_title_compact",
            parent=base["Heading2"],
            fontName="Times-Roman",
            fontSize=15.8,
            leading=19,
            textColor=INK,
            spaceAfter=5,
        ),
        "city_compact": ParagraphStyle(
            "city_compact",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.6,
            leading=9,
            textColor=MUTED,
            spaceAfter=8,
        ),
        "intro_compact": ParagraphStyle(
            "intro_compact",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=9.2,
            leading=12.2,
            textColor=BODY,
            spaceAfter=8,
        ),
        "section_compact": ParagraphStyle(
            "section_compact",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=INK,
            spaceBefore=6,
            spaceAfter=2.5,
        ),
        "body_compact": ParagraphStyle(
            "body_compact",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.8,
            leading=11.2,
            textColor=BODY,
            spaceAfter=2,
        ),
        "body_bold_compact": ParagraphStyle(
            "body_bold_compact",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=9.0,
            leading=11.5,
            textColor=BODY,
            spaceAfter=2.5,
        ),
        "bullet_compact": ParagraphStyle(
            "bullet_compact",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.6,
            leading=10.8,
            textColor=BODY,
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=0,
        ),
        "day_label_ultra": ParagraphStyle(
            "day_label_ultra",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=18.8,
            leading=21.2,
            textColor=INK,
            spaceAfter=1,
        ),
        "day_title_ultra": ParagraphStyle(
            "day_title_ultra",
            parent=base["Heading2"],
            fontName="Times-Roman",
            fontSize=15.2,
            leading=17.8,
            textColor=INK,
            spaceAfter=3,
        ),
        "city_ultra": ParagraphStyle(
            "city_ultra",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.3,
            leading=8.5,
            textColor=MUTED,
            spaceAfter=4,
        ),
        "intro_ultra": ParagraphStyle(
            "intro_ultra",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.7,
            leading=10.6,
            textColor=BODY,
            spaceAfter=5,
        ),
        "section_ultra": ParagraphStyle(
            "section_ultra",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.1,
            leading=8.4,
            textColor=INK,
            spaceBefore=4,
            spaceAfter=1.8,
        ),
        "body_ultra": ParagraphStyle(
            "body_ultra",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.25,
            leading=10.0,
            textColor=BODY,
            spaceAfter=1.2,
        ),
        "body_bold_ultra": ParagraphStyle(
            "body_bold_ultra",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=8.45,
            leading=10.2,
            textColor=BODY,
            spaceAfter=1.5,
        ),
        "bullet_ultra": ParagraphStyle(
            "bullet_ultra",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.05,
            leading=9.7,
            textColor=BODY,
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
            fontSize=8.8,
            leading=12,
            textColor=BODY,
        ),
    }


def standardize_day_typography(styles):
    """Keep day-page font sizes consistent across packed and single-day pages."""
    for base_name in [
        "day_label",
        "day_title",
        "city",
        "intro",
        "section",
        "body",
        "body_bold",
        "bullet",
    ]:
        base_style = styles.get(base_name)
        if not base_style:
            continue
        for suffix in ["compact", "ultra"]:
            variant = styles.get(f"{base_name}_{suffix}")
            if variant:
                variant.fontName = base_style.fontName
                variant.fontSize = base_style.fontSize
                variant.leading = base_style.leading
                variant.textColor = base_style.textColor
    return styles
