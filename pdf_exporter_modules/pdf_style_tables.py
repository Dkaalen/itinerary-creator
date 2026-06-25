"""Table-specific ReportLab paragraph styles."""

from __future__ import annotations

from reportlab.lib.styles import ParagraphStyle

from pdf_exporter_modules import pdf_style_tokens as tokens


def make_table_styles(base):
    return {
        "table_header": ParagraphStyle(
            "table_header",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=tokens.INK,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.6,
            leading=11.6,
            textColor=tokens.BODY,
            splitLongWords=0,
            wordWrap="LTR",
        ),
    }
