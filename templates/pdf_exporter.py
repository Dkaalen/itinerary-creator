from pathlib import Path
import json
import html as html_lib
import re

from bs4 import BeautifulSoup
from text_polish import expand_time_with_duration
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.platypus.doctemplate import LayoutError


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


def clean_text(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def para_text(value):
    return html_lib.escape(clean_text(value))


def has_class(tag, class_name):
    classes = tag.get("class") or []
    return class_name in classes


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
            spaceAfter=14,
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


def add_paragraph(story, text, style, spacer_after=0):
    text = clean_text(text)
    if not text:
        return
    story.append(Paragraph(para_text(text), style))
    if spacer_after:
        story.append(Spacer(1, spacer_after))


def add_bullets(story, items, styles, compact=False, ultra=False):
    """
    Render bullet lists as a two-column table instead of ReportLab's ListFlowable.

    ListFlowable can look acceptable in some viewers, but in generated PDFs it can
    place the bullet glyph on its own baseline/line when text wraps. A tiny table
    gives a stable bullet column and a separate text column, so bullets stay
    visually aligned in the PDF.
    """

    clean_items = [clean_text(item) for item in items if clean_text(item)]
    if not clean_items:
        return

    bullet_style = ParagraphStyle(
        "bullet_symbol",
        parent=styles["bullet_ultra" if ultra else ("bullet_compact" if compact else "bullet")],
        fontName="Helvetica",
        fontSize=7.4 if ultra else (7.6 if compact else 8.2),
        leading=9.8 if ultra else (10.8 if compact else 13),
        textColor=BODY,
        alignment=TA_LEFT,
    )

    rows = []
    for item in clean_items:
        rows.append([
            Paragraph("&#8226;", bullet_style),
            Paragraph(para_text(item), styles["bullet_ultra" if ultra else ("bullet_compact" if compact else "bullet")]),
        ])

    table = Table(
        rows,
        colWidths=[4.0 * mm if compact else 4.5 * mm, 142 * mm],
        hAlign="LEFT",
        splitByRow=True,
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0.6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 4 if compact else 7))


def make_table(data, widths, styles):
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.25)),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def render_cover_page(page, story, styles):
    story.append(Spacer(1, 95 * mm))
    add_paragraph(story, page.select_one(".cover-kicker").get_text(" ") if page.select_one(".cover-kicker") else "Curated Travel Itinerary", styles["cover_kicker"])
    add_paragraph(story, page.select_one(".cover-title").get_text(" ") if page.select_one(".cover-title") else "Itinerary", styles["cover_title"])
    add_paragraph(story, page.select_one(".cover-subtitle").get_text(" ") if page.select_one(".cover-subtitle") else "", styles["cover_subtitle"])
    add_paragraph(story, page.select_one(".cover-destinations").get_text(" ") if page.select_one(".cover-destinations") else "", styles["cover_destinations"])


def render_glance_page(page, story, styles):
    title = page.select_one(".glance-title")
    add_paragraph(story, title.get_text(" ") if title else "Your Trip at a Glance", styles["page_title"])

    rows = []
    for row in page.select(".glance-row"):
        label = row.select_one(".glance-label")
        value = row.select_one(".glance-value")
        if label and value:
            rows.append([
                Paragraph(para_text(label.get_text(" ")), styles["table_header"]),
                Paragraph(para_text(value.get_text(" ")), styles["table_cell"]),
            ])

    if rows:
        story.append(make_table(rows, [38 * mm, 107 * mm], styles))
        story.append(Spacer(1, 14))

    journey_title = page.select_one(".journey-title")
    add_paragraph(story, journey_title.get_text(" ") if journey_title else "Your Journey Arc", styles["page_title"])

    table_rows = []
    header_cells = [clean_text(th.get_text(" ")) for th in page.select(".journey-table th")]
    if header_cells:
        table_rows.append([Paragraph(para_text(cell), styles["table_header"]) for cell in header_cells])

    for tr in page.select(".journey-table tbody tr"):
        cells = [clean_text(td.get_text(" ")) for td in tr.select("td")]
        if cells:
            table_rows.append([Paragraph(para_text(cell), styles["table_cell"]) for cell in cells])

    if table_rows:
        story.append(make_table(table_rows, [34 * mm, 22 * mm, 89 * mm], styles))




def _parse_time_minutes_from_meta(text):
    value = clean_text(text)
    value = re.sub(r"^time\s*:\s*", "", value, flags=re.IGNORECASE).strip()
    if " - " in value or " / " in value:
        return None
    match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(AM|PM)", value, flags=re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    suffix = match.group(3).upper()
    if suffix == "PM" and hour != 12:
        hour += 12
    if suffix == "AM" and hour == 12:
        hour = 0
    return hour * 60 + minute


def _parse_duration_minutes_from_meta(text):
    value = clean_text(text).lower()
    value = re.sub(r"^(?:duration|tour duration|ferry duration|cruise duration)\s*:?\s*", "", value, flags=re.IGNORECASE)
    hour_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:hour|hours|hr|hrs|h)\b", value, flags=re.IGNORECASE)
    minute_match = re.search(r"\b(\d+)\s*(?:minute|minutes|min|mins|m)\b", value, flags=re.IGNORECASE)
    total = 0
    if hour_match:
        total += int(round(float(hour_match.group(1)) * 60))
    if minute_match:
        total += int(minute_match.group(1))
    return total or None


def _format_minutes_as_time(total_minutes):
    total_minutes = total_minutes % (24 * 60)
    hour24 = total_minutes // 60
    minute = total_minutes % 60
    suffix = "AM" if hour24 < 12 else "PM"
    hour12 = hour24 % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def _activity_time_range_text(time_text, duration_text):
    """PDF-side fallback: expand clean single start time + duration to a range."""
    cleaned_time = clean_text(time_text)
    base = re.sub(r"^time\s*:\s*", "", cleaned_time, flags=re.IGNORECASE).strip()
    expanded = expand_time_with_duration(base, duration_text)
    if expanded and expanded != base:
        return f"Time: {expanded}"
    return cleaned_time


def render_content_blocks(container, story, styles, compact=False, ultra=False):
    for child in container.find_all(recursive=False):
        classes = child.get("class") or []
        if "content-block" in classes or "activity-inclusion-block" in classes:
            # Read duration once per activity block so a stale/separate Time line
            # can still be expanded to a start-end range in the PDF export.
            duration_meta_text = ""
            if "activity-block" in classes:
                for possible_meta in child.find_all(recursive=False):
                    meta_text = clean_text(possible_meta.get_text(" "))
                    if re.match(r"^(?:duration|ferry duration|cruise duration)\s*:", meta_text, flags=re.IGNORECASE):
                        duration_meta_text = meta_text
                        break

            for element in child.find_all(recursive=False):
                element_classes = element.get("class") or []

                if "section-title" in element_classes:
                    add_paragraph(story, element.get_text(" "), styles["section_ultra" if ultra else ("section_compact" if compact else "section")])
                elif "activity-inclusion-title" in element_classes:
                    add_paragraph(story, element.get_text(" "), styles["activity_title"])
                elif element.name == "ul":
                    add_bullets(story, [li.get_text(" ") for li in element.find_all("li", recursive=False)], styles, compact=compact, ultra=ultra)
                elif "body-text" in element_classes:
                    text = clean_text(element.get_text(" "))
                    if "activity-block" in classes and re.match(r"^time\s*:", text, flags=re.IGNORECASE):
                        text = _activity_time_range_text(text, duration_meta_text)
                    if "strong-line" in element_classes:
                        add_paragraph(story, text, styles["body_bold_ultra" if ultra else ("body_bold_compact" if compact else "body_bold")])
                    else:
                        add_paragraph(story, text, styles["body_ultra" if ultra else ("body_compact" if compact else "body")])


def add_day_separator(story, styles, ultra=False):
    story.append(Spacer(1, 4 if ultra else 6))
    table = Table([[""]], colWidths=[145 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 0.45, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 5 if ultra else 7))


def render_day_section_pdf(section, story, styles):
    classes = section.get("class") or []
    compact = "packed-section" in classes
    ultra = "triple-packed-section" in classes
    for selector, style_name in [
        (".day-label", "day_label"),
        (".day-title", "day_title"),
        (".city", "city"),
        (".intro", "intro"),
    ]:
        tag = section.select_one(selector)
        if tag:
            style_key = f"{style_name}_ultra" if ultra else (f"{style_name}_compact" if compact else style_name)
            add_paragraph(story, tag.get_text(" "), styles[style_key])

    render_content_blocks(section, story, styles, compact=compact, ultra=ultra)


def render_general_page(page, story, styles):
    # Packed day pages contain one or two explicit day-section elements inside a
    # single A4 page. Render each section in order and keep the PDF page count
    # aligned with the HTML A4 pages.
    day_sections = [child for child in page.find_all(recursive=False) if "day-section" in (child.get("class") or [])]
    if day_sections:
        for index, section in enumerate(day_sections):
            if index > 0:
                add_day_separator(story, styles, ultra="triple-packed-section" in (section.get("class") or []))
            render_day_section_pdf(section, story, styles)
        return

    # Header blocks first
    for selector, style_name in [
        (".final-page-title", "page_title"),
        (".day-label", "day_label"),
        (".day-title", "day_title"),
        (".city", "city"),
        (".intro", "intro"),
    ]:
        tag = page.select_one(selector)
        if tag:
            add_paragraph(story, tag.get_text(" "), styles[style_name])

    render_content_blocks(page, story, styles)

    # For simple list pages, final-page-title is followed by a direct UL.
    for ul in page.find_all("ul", recursive=False):
        add_bullets(story, [li.get_text(" ") for li in ul.find_all("li", recursive=False)], styles)

def export_html_to_pdf(html_path, pdf_path):
    """
    Converts the generated itinerary HTML into an A4 PDF without browser dependencies.

    This intentionally avoids Playwright/Chromium so the PDF export works reliably
    on Streamlit Cloud. The PDF is rebuilt from the itinerary HTML into a clean
    A4 document using ReportLab.
    """

    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    apply_pdf_palette(extract_pdf_palette(soup))
    pages = soup.select(".a4-page")

    styles = make_styles()
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

    for index, page in enumerate(pages):
        classes = page.get("class") or []

        if "cover-page" in classes:
            render_cover_page(page, story, styles)
        elif page.select_one(".glance-card") or page.select_one(".journey-arc"):
            render_glance_page(page, story, styles)
        else:
            render_general_page(page, story, styles)

        if index < len(pages) - 1:
            story.append(PageBreak())

    if not story:
        story.append(Paragraph("Itinerary preview", styles["page_title"]))

    doc.build(story, onFirstPage=page_background, onLaterPages=page_background)

    return pdf_path
