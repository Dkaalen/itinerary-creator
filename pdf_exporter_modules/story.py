import html as html_lib

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

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


def _bullet_para_text(value):
    """Preserve multiline bullet details with a visible continuation indent."""
    text = str(value or "").replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    rendered = []
    for index, line in enumerate(lines):
        prefix = "&nbsp;&nbsp;&nbsp;&nbsp;" if index else ""
        rendered.append(prefix + html_lib.escape(line))
    return "<br/>".join(rendered)


def add_bullets(story, items, styles):
    """Render bullet lists as a table for stable PDF bullet alignment."""

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

    rows = []
    for item in clean_items:
        rows.append([
            Paragraph("&#8226;", bullet_style),
            Paragraph(_bullet_para_text(item), styles["bullet"]),
        ])

    table = Table(
        rows,
        colWidths=[4.5 * mm, 142 * mm],
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
    story.append(Spacer(1, 7))


def make_table(data, widths, styles):
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pdf_styles.CARD),
                ("BOX", (0, 0), (-1, -1), 0.5, pdf_styles.LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, pdf_styles.LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
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
