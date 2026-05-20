from pathlib import Path
import json
import html as html_lib

from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
    HRFlowable,
)


# ── Default colour palette (Classic Agent) ─────────────────────────────────────
PAGE_BACKGROUND = colors.HexColor("#f4efe8")
INK             = colors.HexColor("#1f3446")
BODY            = colors.HexColor("#2f2f2f")
MUTED           = colors.HexColor("#7b746c")
LINE            = colors.HexColor("#d8cec2")
ACCENT          = colors.HexColor("#1f3446")
CARD_BG         = colors.Color(1, 1, 1, alpha=0.42)
CARD_BORDER     = colors.HexColor("#d8cec2")


DEFAULT_PDF_COLORS = {
    "page_bg": "#f4efe8",
    "ink":     "#1f3446",
    "body":    "#2f2f2f",
    "muted":   "#7b746c",
    "line":    "#d8cec2",
    "accent":  "#1f3446",
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
    global PAGE_BACKGROUND, INK, BODY, MUTED, LINE, ACCENT, CARD_BORDER
    color_data = color_data or {}
    PAGE_BACKGROUND = hex_to_color(color_data.get("page_bg"), PAGE_BACKGROUND)
    INK    = hex_to_color(color_data.get("ink"),    INK)
    BODY   = hex_to_color(color_data.get("body"),   BODY)
    MUTED  = hex_to_color(color_data.get("muted"),  MUTED)
    LINE   = hex_to_color(color_data.get("line"),   LINE)
    ACCENT = hex_to_color(color_data.get("accent") or color_data.get("ink"), ACCENT)
    CARD_BORDER = LINE


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
        pass
    return DEFAULT_PDF_COLORS


# ── Utilities ──────────────────────────────────────────────────────────────────
def clean_text(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def para_text(value):
    return html_lib.escape(clean_text(value))


def has_class(tag, class_name):
    return class_name in (tag.get("class") or [])


def page_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAGE_BACKGROUND)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


# ── Typography ─────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    return {
        # ── Cover ──────────────────────────────────────────────────────────────
        "cover_kicker": ParagraphStyle(
            "cover_kicker", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=9, leading=13,
            textColor=MUTED, spaceAfter=10,
        ),
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"],
            fontName="Times-Bold", fontSize=40, leading=46,
            textColor=INK, spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle", parent=base["Normal"],
            fontName="Times-Roman", fontSize=17, leading=23,
            textColor=INK, spaceAfter=14,
        ),
        "cover_destinations": ParagraphStyle(
            "cover_destinations", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=10, leading=14,
            textColor=BODY, spaceBefore=14,
        ),

        # ── Summary / glance page ──────────────────────────────────────────────
        "page_title": ParagraphStyle(
            "page_title", parent=base["Heading1"],
            fontName="Times-Bold", fontSize=22, leading=27,
            textColor=INK, spaceAfter=12,
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=9, leading=13,
            textColor=INK,
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base["Normal"],
            fontName="Helvetica", fontSize=9, leading=13,
            textColor=BODY,
        ),

        # ── Day section — FULL ─────────────────────────────────────────────────
        "day_label": ParagraphStyle(
            "day_label", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=8.5, leading=11,
            textColor=ACCENT, spaceAfter=2,
        ),
        "day_title": ParagraphStyle(
            "day_title", parent=base["Heading2"],
            fontName="Times-Bold", fontSize=22, leading=27,
            textColor=INK, spaceAfter=3,
        ),
        "city": ParagraphStyle(
            "city", parent=base["Normal"],
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=MUTED, spaceAfter=12,
        ),
        "intro": ParagraphStyle(
            "intro", parent=base["Normal"],
            fontName="Times-Roman", fontSize=11.2, leading=15.5,
            textColor=BODY, spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "section", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=7.8, leading=10,
            textColor=ACCENT, spaceBefore=10, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontName="Times-Roman", fontSize=10.5, leading=14,
            textColor=BODY, spaceAfter=2,
        ),
        "body_bold": ParagraphStyle(
            "body_bold", parent=base["Normal"],
            fontName="Times-Bold", fontSize=11, leading=15,
            textColor=INK, spaceAfter=3,
        ),
        "meta": ParagraphStyle(
            "meta", parent=base["Normal"],
            fontName="Helvetica", fontSize=9.5, leading=13,
            textColor=BODY, spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["Normal"],
            fontName="Times-Roman", fontSize=10.2, leading=13.5,
            textColor=BODY, leftIndent=0, firstLineIndent=0, spaceAfter=0,
        ),

        # ── Day section — COMPACT (2-per-page) ────────────────────────────────
        "day_label_compact": ParagraphStyle(
            "day_label_compact", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=7.8, leading=9.5,
            textColor=ACCENT, spaceAfter=1,
        ),
        "day_title_compact": ParagraphStyle(
            "day_title_compact", parent=base["Heading2"],
            fontName="Times-Bold", fontSize=18, leading=22,
            textColor=INK, spaceAfter=2,
        ),
        "city_compact": ParagraphStyle(
            "city_compact", parent=base["Normal"],
            fontName="Helvetica", fontSize=8, leading=10,
            textColor=MUTED, spaceAfter=8,
        ),
        "intro_compact": ParagraphStyle(
            "intro_compact", parent=base["Normal"],
            fontName="Times-Roman", fontSize=9.5, leading=12.8,
            textColor=BODY, spaceAfter=7,
        ),
        "section_compact": ParagraphStyle(
            "section_compact", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=7.2, leading=9,
            textColor=ACCENT, spaceBefore=7, spaceAfter=2,
        ),
        "body_compact": ParagraphStyle(
            "body_compact", parent=base["Normal"],
            fontName="Times-Roman", fontSize=9.2, leading=12.2,
            textColor=BODY, spaceAfter=1.5,
        ),
        "body_bold_compact": ParagraphStyle(
            "body_bold_compact", parent=base["Normal"],
            fontName="Times-Bold", fontSize=9.5, leading=12.8,
            textColor=INK, spaceAfter=2,
        ),
        "meta_compact": ParagraphStyle(
            "meta_compact", parent=base["Normal"],
            fontName="Helvetica", fontSize=8.5, leading=11.5,
            textColor=BODY, spaceAfter=1.5,
        ),
        "bullet_compact": ParagraphStyle(
            "bullet_compact", parent=base["Normal"],
            fontName="Times-Roman", fontSize=8.8, leading=11.5,
            textColor=BODY, leftIndent=0, firstLineIndent=0, spaceAfter=0,
        ),

        # ── Day section — ULTRA (3-per-page) ──────────────────────────────────
        "day_label_ultra": ParagraphStyle(
            "day_label_ultra", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=7.3, leading=8.8,
            textColor=ACCENT, spaceAfter=1,
        ),
        "day_title_ultra": ParagraphStyle(
            "day_title_ultra", parent=base["Heading2"],
            fontName="Times-Bold", fontSize=15.5, leading=19,
            textColor=INK, spaceAfter=2,
        ),
        "city_ultra": ParagraphStyle(
            "city_ultra", parent=base["Normal"],
            fontName="Helvetica", fontSize=7.5, leading=9.5,
            textColor=MUTED, spaceAfter=5,
        ),
        "intro_ultra": ParagraphStyle(
            "intro_ultra", parent=base["Normal"],
            fontName="Times-Roman", fontSize=8.8, leading=11.5,
            textColor=BODY, spaceAfter=5,
        ),
        "section_ultra": ParagraphStyle(
            "section_ultra", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=6.8, leading=8.5,
            textColor=ACCENT, spaceBefore=5, spaceAfter=1.5,
        ),
        "body_ultra": ParagraphStyle(
            "body_ultra", parent=base["Normal"],
            fontName="Times-Roman", fontSize=8.4, leading=10.8,
            textColor=BODY, spaceAfter=1,
        ),
        "body_bold_ultra": ParagraphStyle(
            "body_bold_ultra", parent=base["Normal"],
            fontName="Times-Bold", fontSize=8.6, leading=11,
            textColor=INK, spaceAfter=1.5,
        ),
        "meta_ultra": ParagraphStyle(
            "meta_ultra", parent=base["Normal"],
            fontName="Helvetica", fontSize=7.8, leading=10,
            textColor=BODY, spaceAfter=1,
        ),
        "bullet_ultra": ParagraphStyle(
            "bullet_ultra", parent=base["Normal"],
            fontName="Times-Roman", fontSize=8.1, leading=10.5,
            textColor=BODY, leftIndent=0, firstLineIndent=0, spaceAfter=0,
        ),

        # ── Final list / notes pages ───────────────────────────────────────────
        "final_title": ParagraphStyle(
            "final_title", parent=base["Heading1"],
            fontName="Times-Bold", fontSize=22, leading=27,
            textColor=INK, spaceAfter=14,
        ),
        "activity_title": ParagraphStyle(
            "activity_title", parent=base["Normal"],
            fontName="Times-Bold", fontSize=12, leading=16,
            textColor=INK, spaceBefore=10, spaceAfter=4,
        ),
    }


# ── Helpers ────────────────────────────────────────────────────────────────────
def add_paragraph(story, text, style, spacer_after=0):
    text = clean_text(text)
    if not text:
        return
    story.append(Paragraph(para_text(text), style))
    if spacer_after:
        story.append(Spacer(1, spacer_after))


def add_rule(story, width_mm=145, thickness=0.6, color=None, space_before=3, space_after=6):
    if space_before:
        story.append(Spacer(1, space_before))
    story.append(HRFlowable(
        width=f"{width_mm}mm",
        thickness=thickness,
        color=color or LINE,
        spaceAfter=space_after,
    ))


def add_accent_rule(story, width_mm=28, thickness=1.8, space_after=10):
    """Short bold accent rule beneath day titles."""
    story.append(HRFlowable(
        width=f"{width_mm}mm",
        thickness=thickness,
        color=ACCENT,
        spaceAfter=space_after,
    ))


def _s(styles, key, suffix):
    """Return styles[key+suffix] if it exists, else styles[key]."""
    full = f"{key}{suffix}"
    return styles.get(full, styles.get(key, styles["body"]))


def add_bullets(story, items, styles, compact=False, ultra=False):
    """Two-column bullet table: glyph column + text column."""
    clean_items = [clean_text(item) for item in items if clean_text(item)]
    if not clean_items:
        return

    suffix = "_ultra" if ultra else ("_compact" if compact else "")
    bullet_key = f"bullet{suffix}"
    bst = styles.get(bullet_key, styles["bullet"])

    glyph_style = ParagraphStyle(
        "blt_glyph", parent=bst,
        fontName="Helvetica",
        fontSize=bst.fontSize - 0.5,
        leading=bst.leading,
        textColor=ACCENT,
    )

    col_text = 142 * mm
    col_dot  = 5.5 * mm

    rows = []
    for item in clean_items:
        rows.append([
            Paragraph("&#8226;", glyph_style),
            Paragraph(para_text(item), bst),
        ])

    table = Table(rows, colWidths=[col_dot, col_text], hAlign="LEFT", splitByRow=True)
    table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.8),
    ]))
    story.append(table)
    story.append(Spacer(1, 5 if compact or ultra else 8))


def make_glance_table(data, widths, styles):
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.30)),
        ("BOX",           (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


# ── Day header ─────────────────────────────────────────────────────────────────
def render_day_header(section, story, styles, compact=False, ultra=False):
    """Render Day N label, title, city and accent rule."""
    suffix = "_ultra" if ultra else ("_compact" if compact else "")

    tag_label = section.select_one(".day-label")
    tag_title = section.select_one(".day-title")
    tag_city  = section.select_one(".city")

    label_text = clean_text(tag_label.get_text(" ")) if tag_label else ""
    title_text = clean_text(tag_title.get_text(" ")) if tag_title else ""
    city_text  = clean_text(tag_city.get_text(" "))  if tag_city  else ""

    if label_text:
        story.append(Paragraph(para_text(label_text.upper()), _s(styles, "day_label", suffix)))
    if title_text:
        story.append(Paragraph(para_text(title_text), _s(styles, "day_title", suffix)))

    # Short accent rule beneath title
    rule_w = 20 if ultra else (24 if compact else 30)
    rule_t = 1.2 if ultra else (1.5 if compact else 2.0)
    story.append(HRFlowable(
        width=f"{rule_w}mm", thickness=rule_t,
        color=ACCENT, spaceAfter=4 if ultra else (5 if compact else 8),
    ))

    if city_text:
        story.append(Paragraph(para_text(city_text.upper()), _s(styles, "city", suffix)))


# ── Content blocks ─────────────────────────────────────────────────────────────
def render_content_blocks(container, story, styles, compact=False, ultra=False):
    suffix = "_ultra" if ultra else ("_compact" if compact else "")

    for child in container.find_all(recursive=False):
        classes = child.get("class") or []

        if "content-block" not in classes and "activity-inclusion-block" not in classes:
            continue

        is_activity   = "activity-block"      in classes
        is_hotel      = "accommodation-block" in classes
        is_transport  = "transport-block"     in classes or "travel-sequence-block" in classes or "self-arranged-block" in classes
        is_arrival    = "arrival-block"       in classes
        is_departure  = "departure-block"     in classes
        is_leisure    = "leisure-block"       in classes
        is_inclusion  = "activity-inclusion-block" in classes

        block_items = []

        for element in child.find_all(recursive=False):
            el_classes = element.get("class") or []

            if "section-title" in el_classes:
                raw = clean_text(element.get_text(" "))
                # Style differently depending on block type
                if is_arrival or is_departure:
                    # Use accent colour, larger
                    st = _s(styles, "section", suffix)
                elif is_hotel:
                    st = _s(styles, "section", suffix)
                else:
                    st = _s(styles, "section", suffix)
                block_items.append(("section", raw, st))

            elif "activity-inclusion-title" in el_classes:
                block_items.append(("inclusion_title", clean_text(element.get_text(" ")), styles["activity_title"]))

            elif element.name == "ul":
                items = [li.get_text(" ") for li in element.find_all("li", recursive=False)]
                block_items.append(("bullets", items, None))

            elif "body-text" in el_classes:
                raw = clean_text(element.get_text(" "))
                if not raw:
                    continue
                is_bold = "strong-line" in el_classes
                if is_bold:
                    st = _s(styles, "body_bold", suffix)
                elif "muted-note" in el_classes:
                    st = _s(styles, "body", suffix)
                else:
                    # Meta lines (Time:, Duration:, Meeting point:) rendered smaller
                    # Detect by colon-prefixed label pattern
                    import re as _re
                    if _re.match(r"^(Time|Duration|Meeting point|Pick-up|Drop-off|Departure|Luggage|End point|Location|Destination):", raw):
                        st = _s(styles, "meta", suffix)
                    else:
                        st = _s(styles, "body", suffix)
                block_items.append(("text", raw, st))

        if not block_items:
            continue

        # Wrap activity blocks in a subtle card
        if is_activity and not compact and not ultra:
            _render_activity_card(story, block_items, styles, compact, ultra)
        elif is_hotel and not ultra:
            _render_hotel_card(story, block_items, styles, compact, ultra)
        else:
            _render_plain_block(story, block_items, styles, compact, ultra)


def _render_plain_block(story, items, styles, compact, ultra):
    """Render block items without any card wrapping."""
    for kind, data, st in items:
        if kind == "section":
            add_paragraph(story, data, st)
        elif kind == "inclusion_title":
            add_paragraph(story, data, styles["activity_title"])
        elif kind == "bullets":
            add_bullets(story, data, styles, compact=compact, ultra=ultra)
        elif kind == "text":
            add_paragraph(story, data, st)


def _render_activity_card(story, items, styles, compact, ultra):
    """Render an activity block with a subtle left-border card feel."""
    block_story = []
    for kind, data, st in items:
        if kind == "section":
            block_story.append(Paragraph(para_text(data), st))
        elif kind == "bullets":
            suffix = "_ultra" if ultra else ("_compact" if compact else "")
            bullet_key = f"bullet{suffix}"
            bst = styles.get(bullet_key, styles["bullet"])
            glyph_style = ParagraphStyle("bg", parent=bst, fontName="Helvetica",
                                          fontSize=bst.fontSize-0.5, textColor=ACCENT)
            for item in data:
                item = clean_text(item)
                if item:
                    block_story.append(Table(
                        [[Paragraph("&#8226;", glyph_style), Paragraph(para_text(item), bst)]],
                        colWidths=[5.5*mm, 133*mm], hAlign="LEFT",
                    ))
        elif kind == "text":
            if data:
                block_story.append(Paragraph(para_text(data), st))

    if not block_story:
        return

    # Left-border accent using a 2-col table: thin accent col + content col
    accent_col = Table(
        [[""] for _ in range(len(block_story) + 2)],
        colWidths=[2.2 * mm],
        hAlign="LEFT",
    )
    accent_col.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Build inner content table
    inner_rows = [[item] for item in block_story]
    inner_table = Table(inner_rows, colWidths=[139 * mm], hAlign="LEFT")
    inner_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    # Outer wrapper: left border + content
    outer = Table(
        [[accent_col, inner_table]],
        colWidths=[2.2 * mm, 139 * mm],
        hAlign="LEFT",
    )
    outer.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("BACKGROUND",    (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.28)),
        ("BOX",           (0, 0), (-1, -1), 0.5, CARD_BORDER),
    ]))

    story.append(Spacer(1, 5))
    story.append(outer)
    story.append(Spacer(1, 8))


def _render_hotel_card(story, items, styles, compact, ultra):
    """Render hotel block with a light box and subtle background."""
    block_story = []
    suffix = "_ultra" if ultra else ("_compact" if compact else "")
    for kind, data, st in items:
        if kind == "section":
            block_story.append(Paragraph(para_text(data), st))
        elif kind == "bullets":
            bullet_key = f"bullet{suffix}"
            bst = styles.get(bullet_key, styles["bullet"])
            glyph_style = ParagraphStyle("bg2", parent=bst, fontName="Helvetica",
                                          fontSize=bst.fontSize-0.5, textColor=ACCENT)
            for item in data:
                item = clean_text(item)
                if item:
                    block_story.append(Table(
                        [[Paragraph("&#8226;", glyph_style), Paragraph(para_text(item), bst)]],
                        colWidths=[5.5*mm, 133*mm], hAlign="LEFT",
                    ))
        elif kind == "text":
            if data:
                block_story.append(Paragraph(para_text(data), st))

    if not block_story:
        return

    inner_rows = [[item] for item in block_story]
    inner_table = Table(inner_rows, colWidths=[141 * mm], hAlign="LEFT")
    inner_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BACKGROUND",    (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.40)),
        ("BOX",           (0, 0), (-1, -1), 0.6, LINE),
    ]))

    story.append(Spacer(1, 5))
    story.append(inner_table)
    story.append(Spacer(1, 8))


def add_day_separator(story, styles, ultra=False, compact=False):
    sp = 3 if ultra else (4 if compact else 6)
    story.append(Spacer(1, sp))
    story.append(HRFlowable(
        width="145mm", thickness=0.5,
        color=LINE, spaceAfter=sp + 2,
    ))


# ── Page-level renderers ───────────────────────────────────────────────────────
def render_cover_page(page, story, styles):
    story.append(Spacer(1, 90 * mm))
    kicker = page.select_one(".cover-kicker")
    title  = page.select_one(".cover-title")
    sub    = page.select_one(".cover-subtitle")
    dest   = page.select_one(".cover-destinations")

    add_paragraph(story, kicker.get_text(" ") if kicker else "Curated Travel Itinerary", styles["cover_kicker"])
    add_paragraph(story, title.get_text(" ")  if title  else "Itinerary", styles["cover_title"])

    # Rule under cover title
    story.append(HRFlowable(width="80mm", thickness=1.5, color=ACCENT, spaceAfter=12))

    add_paragraph(story, sub.get_text(" ")  if sub  else "", styles["cover_subtitle"])
    add_paragraph(story, dest.get_text(" ") if dest else "", styles["cover_destinations"])


def render_glance_page(page, story, styles):
    title_el = page.select_one(".glance-title")
    add_paragraph(story, title_el.get_text(" ") if title_el else "Your Trip at a Glance", styles["page_title"])
    story.append(HRFlowable(width="145mm", thickness=0.5, color=LINE, spaceAfter=10))

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
        story.append(make_glance_table(rows, [40 * mm, 105 * mm], styles))
        story.append(Spacer(1, 16))

    jt_el = page.select_one(".journey-title")
    add_paragraph(story, jt_el.get_text(" ") if jt_el else "Your Journey Arc", styles["page_title"])
    story.append(HRFlowable(width="145mm", thickness=0.5, color=LINE, spaceAfter=10))

    table_rows = []
    headers = [clean_text(th.get_text(" ")) for th in page.select(".journey-table th")]
    if headers:
        table_rows.append([Paragraph(para_text(h), styles["table_header"]) for h in headers])
    for tr in page.select(".journey-table tbody tr"):
        cells = [clean_text(td.get_text(" ")) for td in tr.select("td")]
        if cells:
            table_rows.append([Paragraph(para_text(c), styles["table_cell"]) for c in cells])
    if table_rows:
        story.append(make_glance_table(table_rows, [36 * mm, 22 * mm, 87 * mm], styles))


def render_day_section_pdf(section, story, styles):
    classes  = section.get("class") or []
    compact  = "packed-section"        in classes
    ultra    = "triple-packed-section" in classes

    render_day_header(section, story, styles, compact=compact, ultra=ultra)

    tag_intro = section.select_one(".intro")
    if tag_intro:
        suffix = "_ultra" if ultra else ("_compact" if compact else "")
        add_paragraph(story, tag_intro.get_text(" "), _s(styles, "intro", suffix))

    render_content_blocks(section, story, styles, compact=compact, ultra=ultra)


def render_general_page(page, story, styles):
    day_sections = [
        child for child in page.find_all(recursive=False)
        if "day-section" in (child.get("class") or [])
    ]

    if day_sections:
        page_classes = page.get("class") or []
        if "triple-day-page" in page_classes:
            story.append(Spacer(1, 4 * mm))
        elif "packed-day-page" in page_classes:
            story.append(Spacer(1, 7 * mm))
        else:
            story.append(Spacer(1, 10 * mm))

        for idx, section in enumerate(day_sections):
            if idx > 0:
                ultra = "triple-packed-section" in (section.get("class") or [])
                compact = "packed-section" in (section.get("class") or [])
                add_day_separator(story, styles, ultra=ultra, compact=compact)
            render_day_section_pdf(section, story, styles)
        return

    # Final/list pages
    for selector, style_key in [
        (".final-page-title", "final_title"),
        (".day-label",        "day_label"),
        (".day-title",        "day_title"),
        (".city",             "city"),
        (".intro",            "intro"),
    ]:
        tag = page.select_one(selector)
        if tag:
            add_paragraph(story, tag.get_text(" "), styles[style_key])

    render_content_blocks(page, story, styles)

    for ul in page.find_all("ul", recursive=False):
        add_bullets(story, [li.get_text(" ") for li in ul.find_all("li", recursive=False)], styles)


# ── Main export ────────────────────────────────────────────────────────────────
def export_html_to_pdf(html_path, pdf_path):
    """
    Convert the generated itinerary HTML to a polished A4 PDF.
    Uses ReportLab — no browser dependency.
    """
    html_path = Path(html_path).resolve()
    pdf_path  = Path(pdf_path).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    soup  = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    apply_pdf_palette(extract_pdf_palette(soup))
    pages = soup.select(".a4-page")

    styles = make_styles()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title="Itinerary Preview",
        author="Itinerary Creator",
    )

    story = []
    for idx, page in enumerate(pages):
        classes = page.get("class") or []

        if "cover-page" in classes:
            render_cover_page(page, story, styles)
        elif page.select_one(".glance-card") or page.select_one(".journey-arc"):
            render_glance_page(page, story, styles)
        else:
            render_general_page(page, story, styles)

        if idx < len(pages) - 1:
            story.append(PageBreak())

    if not story:
        story.append(Paragraph("Itinerary preview", styles["page_title"]))

    doc.build(story, onFirstPage=page_background, onLaterPages=page_background)
    return pdf_path
