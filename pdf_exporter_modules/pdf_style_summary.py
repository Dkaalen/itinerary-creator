"""Summary-page ReportLab paragraph styles."""

from __future__ import annotations

from reportlab.lib.styles import ParagraphStyle

from pdf_exporter_modules import pdf_style_tokens as tokens


def make_summary_styles(base):
    return {
        "summary_title": ParagraphStyle(
            "summary_title",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=18.5,
            leading=22,
            textColor=tokens.INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=7,
        ),
        "summary_header": ParagraphStyle(
            "summary_header",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10.5,
            textColor=tokens.ACCENT,
            splitLongWords=0,
            wordWrap="LTR",
        ),
        "summary_cell": ParagraphStyle(
            "summary_cell",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.3,
            leading=13.8,
            textColor=tokens.BODY,
            splitLongWords=0,
            wordWrap="LTR",
        ),
    }
