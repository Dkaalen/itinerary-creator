"""Cover-page rendering for typed PDF export."""

from __future__ import annotations

from itinerary_generation.render_model import RenderDocument
from pdf_exporter_modules.cover_page import CoverPageContent, normalize_cover_route_text, render_cover_content


def cover_content(render_document: RenderDocument) -> CoverPageContent:
    cover = render_document.cover
    if not cover:
        return CoverPageContent(
            title=render_document.title or "Itinerary",
            subtitle=render_document.subtitle or "",
            route=normalize_cover_route_text(render_document.route),
        )

    return CoverPageContent(
        kicker=getattr(cover, "kicker", "") or "Travel Itinerary",
        title=getattr(cover, "title", "") or render_document.title or "Itinerary",
        subtitle=getattr(cover, "subtitle", "") or render_document.subtitle or "",
        dates=getattr(cover, "dates", "") or "",
        route_label=getattr(cover, "route_label", "") or "Route",
        route=normalize_cover_route_text(getattr(cover, "route", "") or render_document.route),
        background_path=getattr(cover, "background_path", "") or "",
        crop_focus=getattr(cover, "crop_focus", "") or "top",
        ink=getattr(cover, "ink", "") or "",
        muted=getattr(cover, "muted", "") or "",
    )


def render_cover(render_document: RenderDocument, story, styles, temp_dir):
    render_cover_content(cover_content(render_document), story, styles, temp_dir=temp_dir)
