"""Typed RenderDocument PDF exporter.

This module is now a small orchestration façade. Page-specific rendering lives
in focused modules under ``pdf_exporter_modules`` so PDF layout changes stay
localized.
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping
import tempfile

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

from itinerary_generation.editor_page_contract import final_section_page_id, ordered_page_ids, stable_page_id
from itinerary_generation.render_model import RenderDocument
from pdf_exporter_modules.export_profiles import DEFAULT_PDF_EXPORT_PROFILE, resolve_pdf_export_profile
from pdf_exporter_modules.pdf_cover_renderer import cover_content as _cover_content
from pdf_exporter_modules.pdf_cover_renderer import render_cover as _render_cover
from pdf_exporter_modules.pdf_day_renderer import block_story as _block_story
from pdf_exporter_modules.pdf_day_renderer import build_one_page_day_flowable as _build_one_page_day_flowable
from pdf_exporter_modules.pdf_day_renderer import compact_items as _compact_items
from pdf_exporter_modules.pdf_day_renderer import day_image_has_layout_budget as _day_image_has_layout_budget
from pdf_exporter_modules.pdf_day_renderer import day_label as _day_label
from pdf_exporter_modules.pdf_day_renderer import ellipsize_text as _ellipsize_text
from pdf_exporter_modules.pdf_day_renderer import render_day_story as _render_day_story
from pdf_exporter_modules.pdf_final_section_renderer import render_final_page as _render_final_page
from pdf_exporter_modules.pdf_final_section_renderer import render_final_section as _render_final_section
from pdf_exporter_modules.pdf_final_section_renderer import render_important_notes_final_page as _render_important_notes_final_page
from pdf_exporter_modules.pdf_final_section_renderer import render_supported_final_html as _render_supported_final_html
from pdf_exporter_modules.pdf_html_fallback import _any_final_html_requires_fallback
from pdf_exporter_modules.pdf_html_fallback import _final_content_html_supported
from pdf_exporter_modules.pdf_html_fallback import _iter_html_values
from pdf_exporter_modules.pdf_html_fallback import render_document_requires_html_fallback
from pdf_exporter_modules.pdf_image_renderer import image_path_from_match as _image_path_from_match
from pdf_exporter_modules.pdf_image_renderer import render_day_image_flowable as _render_day_image_flowable
from pdf_exporter_modules.pdf_internal_review_appendix import render_internal_review_appendix as _render_internal_review_appendix
from pdf_exporter_modules.styles import apply_pdf_palette, make_styles, page_background


def export_render_document_to_pdf(
    render_document: RenderDocument,
    pdf_path,
    *,
    color_data: Mapping | None = None,
    day_images: Mapping[str, Mapping | None] | None = None,
    day_image_crop_focus: Mapping[str, str] | None = None,
    export_profile: str | Mapping | None = None,
):
    """Export a typed RenderDocument to PDF without parsing generated HTML."""

    pdf_path = Path(pdf_path).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    apply_pdf_palette(color_data or None)
    profile = resolve_pdf_export_profile(export_profile) if export_profile is not None else DEFAULT_PDF_EXPORT_PROFILE
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=profile.margin_mm * mm,
        leftMargin=profile.margin_mm * mm,
        topMargin=profile.top_margin_mm * mm,
        bottomMargin=profile.bottom_margin_mm * mm,
        title=profile.document_label or profile.label,
        author="Itinerary Creator",
    )
    doc.allowSplitting = 1
    story = []

    with tempfile.TemporaryDirectory(prefix="itinerary_render_document_images_") as image_temp_dir:
        hidden_page_ids = set(getattr(render_document, "hidden_page_ids", []) or [])
        page_renderers = []

        if "cover" not in hidden_page_ids:
            page_renderers.append(("cover", lambda: _render_cover(render_document, story, styles, image_temp_dir)))
        if render_document.summary and "summary" not in hidden_page_ids:
            from pdf_exporter_modules.pdf_summary_renderer import render_summary

            page_renderers.append(("summary", lambda: render_summary(render_document, story, styles, image_temp_dir)))

        for day in render_document.days or []:
            page_id = stable_page_id("day", getattr(day, "day", ""))

            def _make_day_renderer(day=day):
                return lambda: story.append(
                    _build_one_page_day_flowable(
                        day,
                        styles,
                        image_match=(day_images or {}).get(day.day) if day_images else None,
                        crop_focus=(day_image_crop_focus or {}).get(day.day, "top") if day_image_crop_focus else "top",
                        temp_dir=image_temp_dir,
                        doc=doc,
                        min_compact_level=profile.min_compact_level,
                    )
                )

            page_renderers.append((page_id, _make_day_renderer()))

        for section in render_document.final_sections or []:
            section_id = str(getattr(section, "section_id", "") or "")
            page_id = final_section_page_id(section_id) if section_id in {"whats_included", "whats_not_included", "important_travel_notes"} else section_id
            page_renderers.append((page_id, lambda section=section: _render_final_section(section, story, styles)))

        if profile.include_internal_notes:
            page_renderers.append(("internal_review", lambda: _render_internal_review_appendix(render_document, story, styles)))

        renderer_by_id = {page_id: renderer for page_id, renderer in page_renderers}

        for page_id in ordered_page_ids([page_id for page_id, _ in page_renderers], getattr(render_document, "page_order", []) or []):
            if story:
                story.append(PageBreak())
            renderer_by_id[page_id]()

        if not story:
            story.append(Paragraph("Itinerary preview", styles["page_title"]))

        doc.build(story, onFirstPage=page_background, onLaterPages=page_background)

    return pdf_path


__all__ = [
    "export_render_document_to_pdf",
    "render_document_requires_html_fallback",
    "_any_final_html_requires_fallback",
    "_block_story",
    "_build_one_page_day_flowable",
    "_compact_items",
    "_cover_content",
    "_day_image_has_layout_budget",
    "_day_label",
    "_ellipsize_text",
    "_final_content_html_supported",
    "_image_path_from_match",
    "_iter_html_values",
    "_render_cover",
    "_render_day_image_flowable",
    "_render_day_story",
    "_render_final_page",
    "_render_final_section",
    "_render_important_notes_final_page",
    "_render_internal_review_appendix",
    "_render_supported_final_html",
]
