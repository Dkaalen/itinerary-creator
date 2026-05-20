"""
pdf_exporter.py — Premium A4 itinerary PDF renderer.

Design principles
─────────────────
• Day header: numbered kicker label (small caps) + serif title + short rule
• Activities: left-accent card with pill time badge
• Hotels: inset box, clean hierarchy
• Transport: compact dotted timeline list
• All HRFlowable widths use numeric mm (not strings) — required for
  ReportLab ≥ 4.x where string-mm parsing was removed.
"""

from pathlib import Path
import json
import html as html_lib
import re

from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
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

# ── Page dimensions ────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4          # 595.27 × 841.89 
L_MARGIN = R_MARGIN = 22 * mm
T_MARGIN = B_MARGIN = 22 * mm
CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN   # ≈ 551  ≈ 146.6 mm

# ── Default colour palette (Classic Agent) ─────────────────────────────────────
PAGE_BACKGROUND = colors.HexColor("#f4efe8")
INK             = colors.HexColor("#1f3446")
BODY            = colors.HexColor("#2f2f2f")
MUTED           = colors.HexColor("#7b746c")
LINE            = colors.HexColor("#d8cec2")
ACCENT          = colors.HexColor("#1f3446")   # updated from palette if available
ACCENT_LIGHT    = colors.HexColor("#e8dfd5")
WHITE_CARD      = colors.Color(1, 1, 1, alpha=0.45)
WHITE_CARD_SOFT = colors.Color(1, 1, 1, alpha=0.28)

DEFAULT_PDF_COLORS = {
    "page_bg": "#f4efe8",
    "ink":     "#1f3446",
    "body":    "#2f2f2f",
    "muted":   "#7b746c",
    "line":    "#d8cec2",
    "accent":  "#1f3446",
}


# ── Palette helpers ────────────────────────────────────────────────────────────
def hex_to_color(value, fallback):
    try:
        value = str(value or "").strip()
        if not value.startswith("#"):
            return fallback
        return colors.HexColor(value)
    except Exception:
        return fallback


def apply_pdf_palette(color_data):
    global PAGE_BACKGROUND, INK, BODY, MUTED, LINE, ACCENT, ACCENT_LIGHT, WHITE_CARD, WHITE_CARD_SOFT
    color_data = color_data or {}
    PAGE_BACKGROUND = hex_to_color(color_data.get("page_bg"), PAGE_BACKGROUND)
    INK    = hex_to_color(color_data.get("ink"),    INK)
    BODY   = hex_to_color(color_data.get("body"),   BODY)
    MUTED  = hex_to_color(color_data.get("muted"),  MUTED)
    LINE   = hex_to_color(color_data.get("line"),   LINE)
    ACCENT = hex_to_color(color_data.get("accent") or color_data.get("ink"), ACCENT)


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


# ── Text helpers ───────────────────────────────────────────────────────────────
def clean_text(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def esc(value):
    return html_lib.escape(clean_text(value))


# ── Page background ────────────────────────────────────────────────────────────
def page_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAGE_BACKGROUND)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.restoreState()


# ── Typography system ──────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    # Content width in points
    cw = CONTENT_W

    S = {
        # Cover page
        "cover_kicker": ps("cover_kicker",
            fontName="Helvetica-Bold", fontSize=8.5, leading=12,
            textColor=MUTED, spaceAfter=10),
        "cover_title": ps("cover_title",
            fontName="Times-Bold", fontSize=40, leading=46,
            textColor=INK, spaceAfter=8),
        "cover_subtitle": ps("cover_subtitle",
            fontName="Times-Roman", fontSize=16, leading=22,
            textColor=INK, spaceAfter=12),
        "cover_destinations": ps("cover_destinations",
            fontName="Helvetica-Bold", fontSize=9.5, leading=13,
            textColor=MUTED, spaceBefore=10),

        # Summary page
        "page_title": ps("page_title",
            fontName="Times-Bold", fontSize=22, leading=28,
            textColor=INK, spaceAfter=10),
        "table_header": ps("table_header",
            fontName="Helvetica-Bold", fontSize=8.8, leading=12,
            textColor=INK),
        "table_cell": ps("table_cell",
            fontName="Helvetica", fontSize=8.8, leading=12,
            textColor=BODY),

        # Day section — full
        "day_kicker": ps("day_kicker",
            fontName="Helvetica-Bold", fontSize=7.8, leading=10,
            textColor=ACCENT, spaceAfter=2),
        "day_title": ps("day_title",
            fontName="Times-Bold", fontSize=22, leading=27,
            textColor=INK, spaceAfter=0),
        "city_line": ps("city_line",
            fontName="Helvetica", fontSize=8.8, leading=11,
            textColor=MUTED, spaceBefore=8, spaceAfter=12),
        "intro": ps("intro",
            fontName="Times-Roman", fontSize=11, leading=15.5,
            textColor=BODY, spaceAfter=10),

        # Section labels (Morning Experience, Accommodation, etc.)
        "section_label": ps("section_label",
            fontName="Helvetica-Bold", fontSize=7.5, leading=10,
            textColor=ACCENT, spaceBefore=8, spaceAfter=3),

        # Activity content
        "activity_name": ps("activity_name",
            fontName="Times-Bold", fontSize=12.5, leading=16,
            textColor=INK, spaceAfter=3),
        "meta_line": ps("meta_line",
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=MUTED, spaceAfter=1),
        "description": ps("description",
            fontName="Times-Roman", fontSize=9.8, leading=13.5,
            textColor=BODY, spaceAfter=4),
        "bullet": ps("bullet",
            fontName="Times-Roman", fontSize=9.8, leading=13,
            textColor=BODY, leftIndent=0, firstLineIndent=0, spaceAfter=0),

        # Hotel / accommodation
        "hotel_name": ps("hotel_name",
            fontName="Times-Bold", fontSize=11.5, leading=15,
            textColor=INK, spaceAfter=2),
        "hotel_detail": ps("hotel_detail",
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=BODY, spaceAfter=1),

        # Transport / travel
        "transport_title": ps("transport_title",
            fontName="Times-Bold", fontSize=10.5, leading=14,
            textColor=INK, spaceAfter=2),
        "transport_detail": ps("transport_detail",
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=BODY, spaceAfter=1),

        # Departure / arrival
        "event_title": ps("event_title",
            fontName="Times-Bold", fontSize=11, leading=15,
            textColor=INK, spaceAfter=3),
        "event_note": ps("event_note",
            fontName="Times-Roman", fontSize=9.5, leading=13,
            textColor=MUTED, spaceAfter=3),

        # Final pages (What's included, Notes)
        "final_title": ps("final_title",
            fontName="Times-Bold", fontSize=22, leading=28,
            textColor=INK, spaceAfter=12),
        "activity_inclusion_title": ps("activity_inclusion_title",
            fontName="Times-Bold", fontSize=11, leading=15,
            textColor=INK, spaceBefore=10, spaceAfter=4),
        "final_bullet": ps("final_bullet",
            fontName="Times-Roman", fontSize=10, leading=13.5,
            textColor=BODY, leftIndent=0, firstLineIndent=0, spaceAfter=0),
        "notes_body": ps("notes_body",
            fontName="Times-Roman", fontSize=10, leading=14,
            textColor=BODY, spaceAfter=8),

        # ── Compact (2-per-page) variants ──────────────────────────────────────
        "day_kicker_c": ps("day_kicker_c",
            fontName="Helvetica-Bold", fontSize=7.2, leading=9,
            textColor=ACCENT, spaceAfter=1),
        "day_title_c": ps("day_title_c",
            fontName="Times-Bold", fontSize=17, leading=21,
            textColor=INK, spaceAfter=0),
        "city_line_c": ps("city_line_c",
            fontName="Helvetica", fontSize=7.8, leading=10,
            textColor=MUTED, spaceBefore=5, spaceAfter=8),
        "intro_c": ps("intro_c",
            fontName="Times-Roman", fontSize=9.2, leading=12.5,
            textColor=BODY, spaceAfter=7),
        "section_label_c": ps("section_label_c",
            fontName="Helvetica-Bold", fontSize=6.8, leading=9,
            textColor=ACCENT, spaceBefore=5, spaceAfter=2),
        "activity_name_c": ps("activity_name_c",
            fontName="Times-Bold", fontSize=10.2, leading=13,
            textColor=INK, spaceAfter=2),
        "meta_line_c": ps("meta_line_c",
            fontName="Helvetica", fontSize=8, leading=10.5,
            textColor=MUTED, spaceAfter=1),
        "description_c": ps("description_c",
            fontName="Times-Roman", fontSize=8.8, leading=11.8,
            textColor=BODY, spaceAfter=3),
        "bullet_c": ps("bullet_c",
            fontName="Times-Roman", fontSize=8.6, leading=11.2,
            textColor=BODY, leftIndent=0, firstLineIndent=0, spaceAfter=0),
        "hotel_name_c": ps("hotel_name_c",
            fontName="Times-Bold", fontSize=9.8, leading=13,
            textColor=INK, spaceAfter=1),
        "hotel_detail_c": ps("hotel_detail_c",
            fontName="Helvetica", fontSize=7.8, leading=10,
            textColor=BODY, spaceAfter=1),
        "transport_title_c": ps("transport_title_c",
            fontName="Times-Bold", fontSize=9, leading=12,
            textColor=INK, spaceAfter=1),
        "transport_detail_c": ps("transport_detail_c",
            fontName="Helvetica", fontSize=8, leading=10.5,
            textColor=BODY, spaceAfter=1),
        "event_title_c": ps("event_title_c",
            fontName="Times-Bold", fontSize=9.5, leading=12.5,
            textColor=INK, spaceAfter=2),

        # ── Ultra (3-per-page) variants ────────────────────────────────────────
        "day_kicker_u": ps("day_kicker_u",
            fontName="Helvetica-Bold", fontSize=6.6, leading=8,
            textColor=ACCENT, spaceAfter=1),
        "day_title_u": ps("day_title_u",
            fontName="Times-Bold", fontSize=14.5, leading=18,
            textColor=INK, spaceAfter=0),
        "city_line_u": ps("city_line_u",
            fontName="Helvetica", fontSize=7, leading=9,
            textColor=MUTED, spaceBefore=4, spaceAfter=5),
        "intro_u": ps("intro_u",
            fontName="Times-Roman", fontSize=8.4, leading=11,
            textColor=BODY, spaceAfter=5),
        "section_label_u": ps("section_label_u",
            fontName="Helvetica-Bold", fontSize=6.4, leading=8,
            textColor=ACCENT, spaceBefore=4, spaceAfter=1.5),
        "activity_name_u": ps("activity_name_u",
            fontName="Times-Bold", fontSize=9, leading=11.5,
            textColor=INK, spaceAfter=1.5),
        "meta_line_u": ps("meta_line_u",
            fontName="Helvetica", fontSize=7.3, leading=9.5,
            textColor=MUTED, spaceAfter=0.8),
        "description_u": ps("description_u",
            fontName="Times-Roman", fontSize=8, leading=10.5,
            textColor=BODY, spaceAfter=2),
        "bullet_u": ps("bullet_u",
            fontName="Times-Roman", fontSize=7.8, leading=10,
            textColor=BODY, leftIndent=0, firstLineIndent=0, spaceAfter=0),
        "hotel_name_u": ps("hotel_name_u",
            fontName="Times-Bold", fontSize=8.8, leading=11.5,
            textColor=INK, spaceAfter=1),
        "hotel_detail_u": ps("hotel_detail_u",
            fontName="Helvetica", fontSize=7.2, leading=9,
            textColor=BODY, spaceAfter=0.8),
        "transport_title_u": ps("transport_title_u",
            fontName="Times-Bold", fontSize=8.2, leading=10.5,
            textColor=INK, spaceAfter=1),
        "transport_detail_u": ps("transport_detail_u",
            fontName="Helvetica", fontSize=7.3, leading=9.5,
            textColor=BODY, spaceAfter=0.8),
        "event_title_u": ps("event_title_u",
            fontName="Times-Bold", fontSize=8.5, leading=11,
            textColor=INK, spaceAfter=1),
    }
    return S


# ── Style selector helper ──────────────────────────────────────────────────────
def _st(S, key, compact=False, ultra=False):
    """Return the appropriate size variant of a named style."""
    if ultra:
        candidate = S.get(f"{key}_u")
        if candidate:
            return candidate
    if compact:
        candidate = S.get(f"{key}_c")
        if candidate:
            return candidate
    return S.get(key, S["description"])


# ── Low-level story helpers ────────────────────────────────────────────────────
def para(text, style):
    text = clean_text(text)
    if not text:
        return None
    return Paragraph(esc(text), style)


def add(story, flowable):
    if flowable is not None:
        story.append(flowable)


def sp(points):
    return Spacer(1, points)


def rule(width_mm, thickness=0.5, color=None, space_before=0, space_after=4):
    """HRFlowable with numeric mm width — avoids the string-mm crash."""
    items = []
    if space_before:
        items.append(sp(space_before))
    items.append(HRFlowable(
        width=width_mm * mm,      # ← numeric, not string
        thickness=thickness,
        color=color or LINE,
        spaceAfter=space_after,
    ))
    return items


def add_rule(story, width_mm=CONTENT_W / mm, thickness=0.5, color=None,
             space_before=0, space_after=4):
    story.extend(rule(width_mm, thickness, color, space_before, space_after))


def bullets_table(items, S, compact=False, ultra=False, glyph="•"):
    """Two-column bullet table: glyph col + text col. No string-mm widths."""
    clean = [clean_text(i) for i in items if clean_text(i)]
    if not clean:
        return None

    bst = _st(S, "bullet", compact, ultra)
    gst = ParagraphStyle("blt_g", parent=bst,
                         fontName="Helvetica",
                         fontSize=max(6.5, bst.fontSize - 1.2),
                         leading=bst.leading,
                         textColor=ACCENT)

    dot_w = 5 * mm
    txt_w = CONTENT_W - dot_w

    rows = [[Paragraph(glyph, gst), Paragraph(esc(i), bst)] for i in clean]
    tbl = Table(rows, colWidths=[dot_w, txt_w], hAlign="LEFT", splitByRow=True)
    tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.8),
    ]))
    return tbl


# ── Summary-page table ─────────────────────────────────────────────────────────
def summary_table(data, widths_mm):
    widths = [w * mm for w in widths_mm]
    tbl = Table(data, colWidths=widths, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.30)),
        ("BOX",           (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


# ── Activity card ──────────────────────────────────────────────────────────────
def render_activity_card(child, story, S, compact=False, ultra=False):
    """
    Premium activity block:
      ┌────────────────────────────────────────┐
      │ SECTION LABEL (e.g. Morning Experience)│
      │ Activity Title                         │
      │ ○ 10:00 AM  ·  2 hrs  ·  Meeting: ... │
      │ Description text …                     │
      │ • Includes item 1                      │
      │ • Includes item 2                      │
      └────────────────────────────────────────┘
    Rendered as a light card box with an accent top border.
    """
    inner = []

    for el in child.find_all(recursive=False):
        cls = el.get("class") or []

        if "section-title" in cls and "small-section" not in cls:
            # e.g. "Morning Experience"
            txt = clean_text(el.get_text(" "))
            if txt:
                inner.append(para(txt.upper(), _st(S, "section_label", compact, ultra)))

        elif "body-text" in cls and "strong-line" in cls:
            # Activity name
            txt = clean_text(el.get_text(" "))
            if txt:
                inner.append(para(txt, _st(S, "activity_name", compact, ultra)))

        elif "body-text" in cls:
            txt = clean_text(el.get_text(" "))
            if not txt:
                continue
            raw_html = str(el)
            # Meta lines (Time, Duration, Meeting point, etc.)
            if "<span" in raw_html and "meta-label" in raw_html:
                inner.append(para(txt, _st(S, "meta_line", compact, ultra)))
            elif "muted-note" in cls:
                inner.append(para(txt, _st(S, "description", compact, ultra)))
            else:
                inner.append(para(txt, _st(S, "description", compact, ultra)))

        elif "section-title" in cls and "small-section" in cls:
            txt = clean_text(el.get_text(" "))
            if txt:
                inner.append(para(txt.upper(), _st(S, "section_label", compact, ultra)))

        elif el.name == "ul":
            items = [li.get_text(" ") for li in el.find_all("li", recursive=False)]
            bt = bullets_table(items, S, compact, ultra)
            if bt:
                inner.append(bt)

    if not inner:
        return

    # Build card: accent top stripe + white background box
    pad_v = 4 if ultra else (6 if compact else 8)
    pad_h = 6 if ultra else (8 if compact else 10)

    inner_rows = [[item] for item in inner if item is not None]
    if not inner_rows:
        return

    content_tbl = Table(inner_rows, colWidths=[CONTENT_W - 2 * pad_h  /  mm],
                        hAlign="LEFT")
    content_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    card = Table(
        [[content_tbl]],
        colWidths=[CONTENT_W],
        hAlign="LEFT",
    )
    card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.38)),
        ("BOX",           (0, 0), (-1, -1), 0.5, LINE),
        ("LINEABOVE",     (0, 0), (-1, 0),  2.2, ACCENT),
        ("LEFTPADDING",   (0, 0), (-1, -1), pad_h),
        ("RIGHTPADDING",  (0, 0), (-1, -1), pad_h),
        ("TOPPADDING",    (0, 0), (-1, -1), pad_v),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad_v),
    ]))

    story.append(sp(4 if compact or ultra else 6))
    story.append(card)
    story.append(sp(4 if compact or ultra else 8))


# ── Hotel card ─────────────────────────────────────────────────────────────────
def render_hotel_card(child, story, S, compact=False, ultra=False):
    """Light inset card for accommodation blocks."""
    inner = []

    for el in child.find_all(recursive=False):
        cls = el.get("class") or []

        if "section-title" in cls:
            txt = clean_text(el.get_text(" "))
            if txt:
                inner.append(para(txt.upper(), _st(S, "section_label", compact, ultra)))

        elif "body-text" in cls and "strong-line" in cls:
            inner.append(para(clean_text(el.get_text(" ")), _st(S, "hotel_name", compact, ultra)))

        elif "body-text" in cls:
            txt = clean_text(el.get_text(" "))
            if txt:
                inner.append(para(txt, _st(S, "hotel_detail", compact, ultra)))

        elif el.name == "ul":
            items = [li.get_text(" ") for li in el.find_all("li", recursive=False)]
            bt = bullets_table(items, S, compact, ultra)
            if bt:
                inner.append(bt)

    if not inner:
        return

    pad_v = 4 if ultra else (6 if compact else 8)
    pad_h = 6 if ultra else (8 if compact else 10)

    inner_rows = [[item] for item in inner if item is not None]
    if not inner_rows:
        return

    content_tbl = Table(inner_rows, colWidths=[CONTENT_W - 2 * pad_h  /  mm],
                        hAlign="LEFT")
    content_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    card = Table([[content_tbl]], colWidths=[CONTENT_W], hAlign="LEFT")
    card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.25)),
        ("BOX",           (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING",   (0, 0), (-1, -1), pad_h),
        ("RIGHTPADDING",  (0, 0), (-1, -1), pad_h),
        ("TOPPADDING",    (0, 0), (-1, -1), pad_v),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad_v),
    ]))

    story.append(sp(3 if compact or ultra else 5))
    story.append(card)
    story.append(sp(4 if compact or ultra else 7))


# ── Transport / travel block ───────────────────────────────────────────────────
def render_transport_block(child, story, S, compact=False, ultra=False):
    """Clean compact travel arrangement block."""
    for el in child.find_all(recursive=False):
        cls = el.get("class") or []

        if "section-title" in cls:
            txt = clean_text(el.get_text(" "))
            if txt:
                add(story, para(txt.upper(), _st(S, "section_label", compact, ultra)))
                story.append(sp(2))

        elif "body-text" in cls and "strong-line" in cls:
            add(story, para(clean_text(el.get_text(" ")),
                            _st(S, "transport_title", compact, ultra)))

        elif "body-text" in cls:
            txt = clean_text(el.get_text(" "))
            if txt:
                add(story, para(txt, _st(S, "transport_detail", compact, ultra)))

        elif el.name == "ul":
            items = [li.get_text(" ") for li in el.find_all("li", recursive=False)]
            bt = bullets_table(items, S, compact, ultra)
            if bt:
                story.append(bt)
                story.append(sp(3))


# ── Generic / simple block (arrival, leisure, departure, etc.) ─────────────────
def render_simple_block(child, story, S, compact=False, ultra=False):
    for el in child.find_all(recursive=False):
        cls = el.get("class") or []

        if "section-title" in cls:
            txt = clean_text(el.get_text(" "))
            if txt:
                add(story, para(txt.upper(), _st(S, "section_label", compact, ultra)))

        elif "body-text" in cls and "strong-line" in cls:
            add(story, para(clean_text(el.get_text(" ")),
                            _st(S, "event_title", compact, ultra)))

        elif "body-text" in cls:
            txt = clean_text(el.get_text(" "))
            if txt:
                add(story, para(txt, _st(S, "event_note", compact, ultra)))

        elif el.name == "ul":
            items = [li.get_text(" ") for li in el.find_all("li", recursive=False)]
            bt = bullets_table(items, S, compact, ultra)
            if bt:
                story.append(bt)


# ── Dispatcher: choose render function by block class ─────────────────────────
def render_content_block(child, story, S, compact=False, ultra=False):
    cls = set(child.get("class") or [])

    if "activity-block" in cls:
        render_activity_card(child, story, S, compact, ultra)
    elif "accommodation-block" in cls:
        render_hotel_card(child, story, S, compact, ultra)
    elif any(c in cls for c in ("transport-block", "travel-sequence-block",
                                "travel-arrangements-block", "self-arranged-block",
                                "self-transfer-block")):
        render_transport_block(child, story, S, compact, ultra)
    else:
        render_simple_block(child, story, S, compact, ultra)


def render_content_blocks(container, story, S, compact=False, ultra=False):
    for child in container.find_all(recursive=False):
        cls = child.get("class") or []
        if "content-block" in cls or "activity-inclusion-block" in cls:
            render_content_block(child, story, S, compact, ultra)


# ── Day header ─────────────────────────────────────────────────────────────────
def render_day_header(section, story, S, compact=False, ultra=False):
    tag_label = section.select_one(".day-label")
    tag_title = section.select_one(".day-title")
    tag_city  = section.select_one(".city")

    label = clean_text(tag_label.get_text(" ")) if tag_label else ""
    title = clean_text(tag_title.get_text(" ")) if tag_title else ""
    city  = clean_text(tag_city.get_text(" "))  if tag_city  else ""

    # Kicker: "DAY 1" in accent colour, small caps feel
    if label:
        add(story, para(label.upper(), _st(S, "day_kicker", compact, ultra)))

    # Title: large serif
    if title:
        add(story, para(title, _st(S, "day_title", compact, ultra)))

    # Short accent rule under title
    rule_w = 18 if ultra else (22 if compact else 28)
    rule_t = 1.2 if ultra else (1.5 if compact else 2.2)
    story.extend(rule(rule_w, rule_t, ACCENT, space_before=4, space_after=0))

    # City in muted Helvetica
    if city:
        add(story, para(city.upper(), _st(S, "city_line", compact, ultra)))


# ── Day section ────────────────────────────────────────────────────────────────
def render_day_section_pdf(section, story, S):
    cls     = section.get("class") or []
    compact = "packed-section"        in cls
    ultra   = "triple-packed-section" in cls

    render_day_header(section, story, S, compact, ultra)

    tag_intro = section.select_one(".intro")
    if tag_intro:
        txt = clean_text(tag_intro.get_text(" "))
        if txt:
            add(story, para(txt, _st(S, "intro", compact, ultra)))

    render_content_blocks(section, story, S, compact, ultra)


def add_day_separator(story, S, ultra=False, compact=False):
    sp_val = 3 if ultra else (4 if compact else 6)
    story.append(sp(sp_val))
    story.extend(rule(CONTENT_W / mm, 0.4, LINE, space_before=0, space_after=sp_val))


# ── Page renderers ─────────────────────────────────────────────────────────────
def render_cover_page(page, story, S):
    story.append(sp(88 * mm))

    kicker = page.select_one(".cover-kicker")
    title  = page.select_one(".cover-title")
    sub    = page.select_one(".cover-subtitle")
    dest   = page.select_one(".cover-destinations")

    add(story, para(clean_text(kicker.get_text(" ")) if kicker else "Curated Travel Itinerary", S["cover_kicker"]))
    add(story, para(clean_text(title.get_text(" "))  if title  else "Itinerary",               S["cover_title"]))

    # Bold rule beneath cover title
    story.extend(rule(60, 1.8, ACCENT, space_before=4, space_after=10))

    add(story, para(clean_text(sub.get_text(" "))  if sub  else "", S["cover_subtitle"]))
    add(story, para(clean_text(dest.get_text(" ")) if dest else "", S["cover_destinations"]))


def render_glance_page(page, story, S):
    title_el = page.select_one(".glance-title")
    add(story, para(clean_text(title_el.get_text(" ")) if title_el else "Your Trip at a Glance", S["page_title"]))
    story.extend(rule(CONTENT_W / mm, 0.5, LINE, space_before=0, space_after=10))

    rows = []
    for row in page.select(".glance-row"):
        lbl = row.select_one(".glance-label")
        val = row.select_one(".glance-value")
        if lbl and val:
            rows.append([
                Paragraph(esc(clean_text(lbl.get_text(" "))), S["table_header"]),
                Paragraph(esc(clean_text(val.get_text(" "))), S["table_cell"]),
            ])
    if rows:
        story.append(summary_table(rows, [40, CONTENT_W / mm - 40]))
        story.append(sp(14))

    jt_el = page.select_one(".journey-title")
    add(story, para(clean_text(jt_el.get_text(" ")) if jt_el else "Your Journey Arc", S["page_title"]))
    story.extend(rule(CONTENT_W / mm, 0.5, LINE, space_before=0, space_after=10))

    arc_rows = []
    hdrs = [clean_text(th.get_text(" ")) for th in page.select(".journey-table th")]
    if hdrs:
        arc_rows.append([Paragraph(esc(h), S["table_header"]) for h in hdrs])
    for tr in page.select(".journey-table tbody tr"):
        cells = [clean_text(td.get_text(" ")) for td in tr.select("td")]
        if cells:
            arc_rows.append([Paragraph(esc(c), S["table_cell"]) for c in cells])
    if arc_rows:
        col_w = [36, 20, CONTENT_W / mm - 56]
        story.append(summary_table(arc_rows, col_w))


def render_final_page(page, story, S):
    """What's included / Notes / Activity inclusions pages."""
    for selector, style_key in [
        (".final-page-title", "final_title"),
    ]:
        tag = page.select_one(selector)
        if tag:
            add(story, para(clean_text(tag.get_text(" ")), S[style_key]))
            story.extend(rule(CONTENT_W / mm, 0.5, LINE, space_before=0, space_after=10))

    for child in page.find_all(recursive=False):
        cls = child.get("class") or []

        if "final-page-title" in cls:
            continue  # already rendered

        if "content-block" in cls:
            for el in child.find_all(recursive=False):
                el_cls = el.get("class") or []
                if el.name == "ul":
                    items = [li.get_text(" ") for li in el.find_all("li", recursive=False)]
                    bt = bullets_table(items, S, glyph="•")
                    if bt:
                        story.append(bt)
                        story.append(sp(6))
                elif "body-text" in el_cls or "note-paragraph" in el_cls:
                    txt = clean_text(el.get_text(" "))
                    if txt:
                        add(story, para(txt, S["notes_body"]))

        elif "activity-inclusion-block" in cls:
            for el in child.find_all(recursive=False):
                el_cls = el.get("class") or []
                if "activity-inclusion-title" in el_cls:
                    add(story, para(clean_text(el.get_text(" ")),
                                    S["activity_inclusion_title"]))
                    story.extend(rule(30, 0.8, LINE, space_before=0, space_after=4))
                elif el.name == "ul":
                    items = [li.get_text(" ") for li in el.find_all("li", recursive=False)]
                    bt = bullets_table(items, S, glyph="•")
                    if bt:
                        story.append(bt)
                        story.append(sp(4))

    # Handle bare <ul> elements directly on the page
    for ul in page.find_all("ul", recursive=False):
        items = [li.get_text(" ") for li in ul.find_all("li", recursive=False)]
        bt = bullets_table(items, S, glyph="•")
        if bt:
            story.append(bt)
            story.append(sp(6))


def render_general_page(page, story, S):
    day_sections = [
        ch for ch in page.find_all(recursive=False)
        if "day-section" in (ch.get("class") or [])
    ]

    if day_sections:
        page_cls = page.get("class") or []
        if "triple-day-page" in page_cls:
            story.append(sp(4 * mm))
        elif "packed-day-page" in page_cls:
            story.append(sp(6 * mm))
        else:
            story.append(sp(9 * mm))

        for idx, section in enumerate(day_sections):
            if idx > 0:
                ultra = "triple-packed-section" in (section.get("class") or [])
                cmpct = "packed-section"        in (section.get("class") or [])
                add_day_separator(story, S, ultra=ultra, compact=cmpct)
            render_day_section_pdf(section, story, S)
        return

    render_final_page(page, story, S)


# ── Main export ────────────────────────────────────────────────────────────────
def export_html_to_pdf(html_path, pdf_path):
    """
    Convert generated itinerary HTML → premium A4 PDF.
    No browser dependency — uses ReportLab only.
    """
    html_path = Path(html_path).resolve()
    pdf_path  = Path(pdf_path).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    soup  = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    apply_pdf_palette(extract_pdf_palette(soup))

    pages = soup.select(".a4-page")

    S   = make_styles()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=L_MARGIN,
        rightMargin=R_MARGIN,
        topMargin=T_MARGIN,
        bottomMargin=B_MARGIN,
        title="Itinerary",
        author="Itinerary Creator",
    )

    story = []
    for idx, page in enumerate(pages):
        cls = page.get("class") or []

        if "cover-page" in cls:
            render_cover_page(page, story, S)
        elif page.select_one(".glance-card") or page.select_one(".journey-arc"):
            render_glance_page(page, story, S)
        else:
            render_general_page(page, story, S)

        if idx < len(pages) - 1:
            story.append(PageBreak())

    if not story:
        story.append(Paragraph("Itinerary preview", S["page_title"]))

    doc.build(story, onFirstPage=page_background, onLaterPages=page_background)
    return pdf_path
