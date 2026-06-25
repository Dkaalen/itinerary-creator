"""Day-page ReportLab paragraph styles."""

from __future__ import annotations

from reportlab.lib.styles import ParagraphStyle

from pdf_exporter_modules import pdf_style_tokens as tokens


def make_day_styles(base):
    return {
        "day_label": ParagraphStyle(
            "day_label",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=25,
            leading=29,
            textColor=tokens.INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=3,
        ),
        "day_kicker": ParagraphStyle(
            "day_kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.4,
            leading=12.5,
            textColor=tokens.ACCENT,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=9,
        ),
        "day_title": ParagraphStyle(
            "day_title",
            parent=base["Heading2"],
            fontName="Times-Roman",
            fontSize=20,
            leading=24,
            textColor=tokens.INK,
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
            textColor=tokens.MUTED,
            spaceAfter=14,
        ),
        "intro": ParagraphStyle(
            "intro",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=11.5,
            leading=16,
            textColor=tokens.BODY,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=14,
        ),
    }
