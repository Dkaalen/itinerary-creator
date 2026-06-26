"""Shared cover-page PDF rendering helpers."""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.platypus import Spacer, Table, TableStyle

from . import styles as pdf_styles
from .pdf_branding import is_booknordics_pdf
from .image_flowables import FullPageBackgroundImage
from .render_flowables import CoverEmblem, add_cover_rule
from .story import add_paragraph


@dataclass(slots=True)
class CoverPageContent:
    """Renderer-neutral cover content used by HTML and typed PDF exporters."""

    kicker: str = "Travel Itinerary"
    title: str = "Itinerary"
    subtitle: str = ""
    dates: str = ""
    route_label: str = "Route"
    route: str = ""
    background_path: str | Path | None = None
    crop_focus: str = "top"
    ink: str = ""
    muted: str = ""


def cover_color(value, fallback):
    return pdf_styles.hex_to_color(value, fallback)


def cover_styles(content: CoverPageContent, styles):
    cover_styles = dict(styles)
    ink = cover_color(content.ink, pdf_styles.INK)
    muted = cover_color(content.muted, pdf_styles.MUTED)
    body = cover_color(content.ink, pdf_styles.BODY)
    route_label_color = pdf_styles.ACCENT if is_booknordics_pdf() else muted
    for name, color in {
        "cover_kicker": muted,
        "cover_title": ink,
        "cover_subtitle": ink,
        "cover_dates": muted,
        "cover_route_label": route_label_color,
        "cover_destinations": body,
    }.items():
        if name in cover_styles:
            style = copy(cover_styles[name])
            style.textColor = color
            cover_styles[name] = style
    return cover_styles


def normalize_cover_route_text(value: str) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    parts = [" ".join(part.split()) for part in text.replace(" · ", "\n").split("\n") if " ".join(part.split())]
    return " · ".join(parts)


def _append_cover_emblem(story, color):
    emblem = Table([[CoverEmblem(color=color)]], colWidths=[15 * mm], hAlign="CENTER")
    emblem.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(emblem)


def _append_cover_text(story, content: CoverPageContent, resolved_styles, accent):
    _append_cover_emblem(story, accent)
    story.append(Spacer(1, 6 * mm))
    add_paragraph(story, content.kicker or "Travel Itinerary", resolved_styles["cover_kicker"])
    add_cover_rule(story, width=50 * mm, space_after=4, color=accent)
    add_paragraph(story, content.title or "Itinerary", resolved_styles["cover_title"])
    add_cover_rule(story, width=42 * mm, space_after=3, color=accent)
    add_paragraph(story, content.subtitle or "", resolved_styles["cover_subtitle"])
    if content.dates:
        add_paragraph(story, content.dates, resolved_styles["cover_dates"])
    story.append(Spacer(1, 4 * mm))
    add_paragraph(story, content.route_label or "Route", resolved_styles["cover_route_label"])
    add_paragraph(story, str(content.route or "").upper(), resolved_styles["cover_destinations"])


def _append_booknordics_cover_text(story, content: CoverPageContent, resolved_styles, accent):
    _append_cover_emblem(story, accent)
    story.append(Spacer(1, 6 * mm))
    add_paragraph(story, content.kicker or "Travel Itinerary", resolved_styles["cover_kicker"])
    add_paragraph(story, content.title or "Itinerary", resolved_styles["cover_title"])
    add_paragraph(story, content.subtitle or "", resolved_styles["cover_subtitle"])
    if content.dates:
        add_paragraph(story, content.dates, resolved_styles["cover_dates"])
    add_cover_rule(story, width=42 * mm, space_after=4, color=accent)
    add_paragraph(story, content.route_label or "Route", resolved_styles["cover_route_label"])
    add_paragraph(story, str(content.route or "").upper(), resolved_styles["cover_destinations"])


def render_cover_content(content: CoverPageContent, story, styles, temp_dir=None):
    """Append the shared cover flowables to ``story``."""

    resolved_styles = cover_styles(content, styles)
    muted = cover_color(content.muted, pdf_styles.MUTED)
    accent = pdf_styles.ACCENT if is_booknordics_pdf() else muted
    background_path = Path(str(content.background_path or ""))
    if background_path.exists() and background_path.is_file() and temp_dir:
        story.append(FullPageBackgroundImage(background_path, temp_dir, crop_focus=content.crop_focus or "top"))

    if is_booknordics_pdf():
        story.append(Spacer(1, 1 * mm))
        _append_booknordics_cover_text(story, content, resolved_styles, accent)
        return

    story.append(Spacer(1, 9 * mm))
    _append_cover_text(story, content, resolved_styles, accent)
