"""Cover-page PDF rendering."""

from reportlab.lib.units import mm
from reportlab.platypus import Spacer, Table, TableStyle

from . import styles as pdf_styles
from .html_utils import clean_text
from .image_flowables import FullPageBackgroundImage
from .image_paths import resolve_image_path
from .render_flowables import CoverEmblem, add_cover_rule
from .render_text import text_with_line_breaks
from .story import add_paragraph


def render_cover_page(page, story, styles, html_path=None, temp_dir=None):
    # Draw the static seasonal artwork first; all text remains editable/rendered.
    background_path = resolve_image_path(page.get("data-cover-background-path"), html_path) if html_path else None
    if background_path and temp_dir:
        story.append(FullPageBackgroundImage(background_path, temp_dir, crop_focus="top"))

    story.append(Spacer(1, 9 * mm))
    emblem = Table([[CoverEmblem(color=pdf_styles.MUTED)]], colWidths=[15 * mm], hAlign="CENTER")
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
    add_cover_rule(story, width=50 * mm, space_after=4)
    add_paragraph(story, page.select_one(".cover-title").get_text(" ") if page.select_one(".cover-title") else "Itinerary", styles["cover_title"])
    add_cover_rule(story, width=42 * mm, space_after=3)
    subtitle = text_with_line_breaks(page.select_one(".cover-subtitle"))
    add_paragraph(story, subtitle, styles["cover_subtitle"])
    dates = page.select_one(".cover-dates")
    if dates:
        add_paragraph(story, dates.get_text(" "), styles["cover_dates"])
    story.append(Spacer(1, 4 * mm))
    add_paragraph(story, "Route", styles["cover_route_label"])
    route_text = page.select_one(".cover-destinations").get_text(" ") if page.select_one(".cover-destinations") else ""
    add_paragraph(story, clean_text(route_text).upper(), styles["cover_destinations"])
