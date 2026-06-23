import html as html_lib

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from . import styles as pdf_styles
from .html_utils import clean_text, para_text


def add_paragraph(story, text, style, spacer_after=0):
    rendered = para_text(text)
    if not rendered:
        return
    story.append(Paragraph(rendered, style))
    if spacer_after:
        story.append(Spacer(1, spacer_after))


def _clean_bullet_text(value):
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    if "\n" not in text:
        return clean_text(text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _bullet_lines(value):
    text = str(value or "").replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return [line for line in lines if line]


def _bullet_item_table(item, styles, bullet_style):
    lines = _bullet_lines(item)
    if not lines:
        return None
    rows = [[
        Paragraph("&#8226;", bullet_style),
        Paragraph(html_lib.escape(lines[0]), styles["bullet"]),
    ]]
    for continuation in lines[1:]:
        rows.append([
            Paragraph("", bullet_style),
            Paragraph(html_lib.escape(continuation), styles["bullet_continuation"]),
        ])
    table = Table(
        rows,
        colWidths=[4.5 * mm, 142 * mm],
        hAlign="LEFT",
        splitByRow=False,
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
    return table


def add_bullets(story, items, styles, *, spacer_after=7):
    """Render bullet lists with each logical item kept together.

    Multi-line items such as final-page flight inclusions are one client-facing
    unit: bullet label, time and baggage/details must not split across pages.
    The list may still break between separate items.
    """

    clean_items = [_clean_bullet_text(item) for item in items if _clean_bullet_text(item)]
    if not clean_items:
        return

    bullet_style = ParagraphStyle(
        "bullet_symbol",
        parent=styles["bullet"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=13,
        textColor=pdf_styles.BODY,
        alignment=TA_LEFT,
    )

    for item in clean_items:
        table = _bullet_item_table(item, styles, bullet_style)
        if table is not None:
            story.append(KeepTogether([table]))

    if spacer_after:
        story.append(Spacer(1, spacer_after))


def make_table(data, widths, styles):
    """Render premium proposal tables without spreadsheet-style boxing.

    Summary/Journey tables are client-facing itinerary content, not raw data
    grids.  Keep the structure readable, but use whitespace and fine horizontal
    rules instead of heavy cell boxes.
    """

    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, pdf_styles.LINE),
            ]
        )
    )
    return table


def story_height(flowables, available_width):
    """Conservative height estimate for one A4 page story fragment."""
    total = 0
    for flowable in flowables:
        try:
            _, height = flowable.wrap(available_width, 10_000)
        except Exception:
            height = 0
        total += getattr(flowable, "spaceBefore", 0) or 0
        total += height or 0
        total += getattr(flowable, "spaceAfter", 0) or 0
    return total
