"""Cover-specific ReportLab paragraph styles."""

from __future__ import annotations

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle

from pdf_exporter_modules import pdf_style_tokens as tokens


def make_cover_styles(base):
    return {
        "cover_kicker": ParagraphStyle(
            "cover_kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=12,
            textColor=tokens.MUTED,
            uppercase=True,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=38,
            leading=41,
            textColor=tokens.INK,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=15.5,
            leading=20,
            textColor=tokens.INK,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_dates": ParagraphStyle(
            "cover_dates",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=tokens.MUTED,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_route_label": ParagraphStyle(
            "cover_route_label",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=tokens.MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_destinations": ParagraphStyle(
            "cover_destinations",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.8,
            leading=14,
            textColor=tokens.BODY,
            alignment=TA_CENTER,
            spaceBefore=0,
        ),
    }
