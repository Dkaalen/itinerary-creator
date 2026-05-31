"""Cover-page PDF rendering."""

from copy import copy

from reportlab.lib.units import mm
from reportlab.platypus import Spacer, Table, TableStyle

from . import styles as pdf_styles
from .html_utils import clean_text
from .image_flowables import FullPageBackgroundImage
from .image_paths import resolve_image_path
from .render_flowables import CoverEmblem, add_cover_rule
from .render_text import text_with_line_breaks
from .story import add_paragraph


def _cover_color(page, attr, fallback):
    return pdf_styles.hex_to_color(page.get(attr), fallback)


def _cover_styles(page, styles):
    cover_styles = dict(styles)
    ink = _cover_color(page, "data-cover-ink", pdf_styles.INK)
    muted = _cover_color(page, "data-cover-muted", pdf_styles.MUTED)
    body = _cover_color(page, "data-cover-ink", pdf_styles.BODY)
    for name, color in {
        "cover_kicker": muted,
        "cover_title": ink,
        "cover_subtitle": ink,
        "cover_dates": muted,
        "cover_route_label": muted,
        "cover_destinations": body,
    }.items():
        if name in cover_styles:
            style = copy(cover_styles[name])
            style.textColor = color
            cover_styles[name] = style
    return cover_styles


def render_cover_page(page, story, styles, html_path=None, temp_dir=None):
    styles = _cover_styles(page, styles)
    muted = _cover_color(page, "data-cover-muted", pdf_styles.MUTED)
    # Draw the static seasonal artwork first; all text remains editable/rendered.
    background_path = resolve_image_path(page.get("data-cover-background-path"), html_path) if html_path else None
    if background_path and temp_dir:
        story.append(FullPageBackgroundImage(background_path, temp_dir, crop_focus="top"))

    story.append(Spacer(1, 9 * mm))
    emblem = Table([[CoverEmblem(color=muted)]], colWidths=[15 * mm], hAlign="CENTER")
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
    story.append(Spacer(1, 6 * mm))
    add_paragraph(story, page.select_one(".cover-kicker").get_text(" ") if page.select_one(".cover-kicker") else "Travel Itinerary", styles["cover_kicker"])
    add_cover_rule(story, width=50 * mm, space_after=4, color=muted)
    add_paragraph(story, page.select_one(".cover-title").get_text(" ") if page.select_one(".cover-title") else "Itinerary", styles["cover_title"])
    add_cover_rule(story, width=42 * mm, space_after=3, color=muted)
    subtitle = text_with_line_breaks(page.select_one(".cover-subtitle"))
    add_paragraph(story, subtitle, styles["cover_subtitle"])
    dates = page.select_one(".cover-dates")
    if dates:
        add_paragraph(story, dates.get_text(" "), styles["cover_dates"])
    story.append(Spacer(1, 4 * mm))
    add_paragraph(story, "Route", styles["cover_route_label"])
    route_text = text_with_line_breaks(page.select_one(".cover-destinations"))
    add_paragraph(story, route_text.upper(), styles["cover_destinations"])
