"""Decorative ReportLab flowables and rules for PDF rendering."""

from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Spacer, Table, TableStyle

from . import styles as pdf_styles


class CoverEmblem(Flowable):
    """Small centered circular cover emblem used by the PDF cover."""

    def __init__(self, size=15 * mm, color=None):
        super().__init__()
        self.width = float(size)
        self.height = float(size)
        self.color = color or pdf_styles.MUTED

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def split(self, availWidth, availHeight):
        return []

    def draw(self):
        canv = self.canv
        canv.saveState()
        canv.setStrokeColor(self.color)
        canv.setFillColor(self.color)
        canv.setLineWidth(0.45)
        radius = self.width / 2.0
        canv.circle(radius, radius, radius - 0.8, stroke=1, fill=0)
        canv.setFont("Times-Roman", 10)
        canv.drawCentredString(radius, radius - 3.2, "✦")
        canv.restoreState()


class CenterDiamondRule(Flowable):
    """Centered thin rule with a small diamond, matching the HTML cover accent."""

    def __init__(self, width=44 * mm, height=7 * mm, color=None):
        super().__init__()
        self.width = float(width)
        self.height = float(height)
        self.color = color or pdf_styles.MUTED

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def split(self, availWidth, availHeight):
        return []

    def draw(self):
        canv = self.canv
        y = self.height / 2.0
        canv.saveState()
        canv.setStrokeColor(self.color)
        canv.setFillColor(self.color)
        canv.setLineWidth(0.35)
        canv.line(0, y, self.width, y)
        diamond = 2.0
        x = self.width / 2.0
        path = canv.beginPath()
        path.moveTo(x, y + diamond)
        path.lineTo(x + diamond, y)
        path.lineTo(x, y - diamond)
        path.lineTo(x - diamond, y)
        path.close()
        canv.drawPath(path, stroke=0, fill=1)
        canv.restoreState()


def add_premium_rule(story, width=32 * mm, space_after=9):
    """Add a thin editorial accent rule below major headings."""
    table = Table([[""]], colWidths=[width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 0.45, pdf_styles.LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, space_after))


def add_cover_rule(story, width=44 * mm, space_after=9, color=None):
    table = Table([[CenterDiamondRule(width=width, color=color or pdf_styles.MUTED)]], colWidths=[width], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, space_after))
