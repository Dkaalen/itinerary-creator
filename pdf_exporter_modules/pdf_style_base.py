"""Shared PDF body, editor, and bullet styles."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from pdf_exporter_modules import pdf_style_tokens as tokens


def _page_and_body_styles(base):
    return {
        "page_title": ParagraphStyle(
            "page_title",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=25,
            leading=30,
            textColor=tokens.INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=7,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=tokens.INK,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.2,
            leading=14,
            textColor=tokens.BODY,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=3,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=10.5,
            leading=14,
            textColor=tokens.BODY,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=4,
        ),
        "activity_title": ParagraphStyle(
            "activity_title",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=13.5,
            leading=17,
            textColor=tokens.INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceBefore=10,
            spaceAfter=5,
        ),
    }


def _editor_styles(base):
    return {
        "editor_small_note": ParagraphStyle(
            "editor_small_note",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.5,
            textColor=tokens.MUTED,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=3,
        ),
        "editor_large": ParagraphStyle(
            "editor_large",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=11.8,
            leading=15.5,
            textColor=tokens.BODY,
            splitLongWords=0,
            wordWrap="LTR",
            spaceAfter=5,
        ),
        "editor_heading": ParagraphStyle(
            "editor_heading",
            parent=base["Heading3"],
            fontName="Times-Bold",
            fontSize=15.2,
            leading=18.5,
            textColor=tokens.INK,
            splitLongWords=0,
            wordWrap="LTR",
            spaceBefore=8,
            spaceAfter=5,
        ),
        "editor_subheading": ParagraphStyle(
            "editor_subheading",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=11.4,
            textColor=tokens.ACCENT,
            splitLongWords=0,
            wordWrap="LTR",
            spaceBefore=6,
            spaceAfter=4,
        ),
        "editor_note": ParagraphStyle(
            "editor_note",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.8,
            textColor=tokens.MUTED,
            leftIndent=7,
            borderColor=colors.HexColor("#c58a24"),
            borderWidth=0.7,
            borderPadding=5,
            splitLongWords=0,
            wordWrap="LTR",
            spaceBefore=4,
            spaceAfter=6,
        ),
    }


def _bullet_styles(base):
    return {
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.0,
            leading=13,
            textColor=tokens.BODY,
            splitLongWords=0,
            wordWrap="LTR",
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=0,
        ),
        "bullet_continuation": ParagraphStyle(
            "bullet_continuation",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.0,
            leading=13,
            textColor=tokens.MUTED,
            splitLongWords=0,
            wordWrap="LTR",
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=0,
        ),
    }


def make_base_styles(base):
    styles = {}
    styles.update(_page_and_body_styles(base))
    styles.update(_editor_styles(base))
    styles.update(_bullet_styles(base))
    return styles
