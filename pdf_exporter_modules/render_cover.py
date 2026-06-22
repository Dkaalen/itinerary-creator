"""Cover-page PDF rendering."""

from .cover_page import CoverPageContent, render_cover_content
from .image_paths import resolve_image_path
from .render_text import text_with_line_breaks


def _text(page, selector: str, fallback: str = "") -> str:
    element = page.select_one(selector)
    return element.get_text(" ") if element else fallback


def render_cover_page(page, story, styles, html_path=None, temp_dir=None):
    """Render the HTML preview cover page into PDF flowables."""

    background_path = resolve_image_path(page.get("data-cover-background-path"), html_path) if html_path else None
    content = CoverPageContent(
        kicker=_text(page, ".cover-kicker", "Travel Itinerary"),
        title=_text(page, ".cover-title", "Itinerary"),
        subtitle=text_with_line_breaks(page.select_one(".cover-subtitle")),
        dates=_text(page, ".cover-dates", ""),
        route_label=_text(page, ".cover-destination-label", "Route"),
        route=text_with_line_breaks(page.select_one(".cover-destinations")),
        background_path=background_path,
        crop_focus=page.get("data-cover-crop-focus") or "top",
        ink=page.get("data-cover-ink") or "",
        muted=page.get("data-cover-muted") or "",
    )
    render_cover_content(content, story, styles, temp_dir=temp_dir)
