"""Table/card helpers for PDF story rendering."""

from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle

from . import styles as pdf_styles


def boxed_story_table(flowables, width=160 * mm, padding=11, background=None):
    table = Table([[flowables]], colWidths=[width], hAlign="LEFT")
    card_background = background if background is not None else pdf_styles.CARD
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), card_background),
                ("BOX", (0, 0), (-1, -1), 0.35, pdf_styles.LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table
