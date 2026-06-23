"""Typed RenderDocument PDF exporter.

This path builds ReportLab flowables directly from ``RenderDocument`` instead of
scraping day/final content out of the generated preview HTML. The legacy HTML
exporter remains available for visual-editor HTML compatibility while the model
contract is expanded.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString
from pathlib import Path
import base64
import re
import tempfile
from typing import Mapping

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from itinerary_generation.render_model import RenderBlock, RenderDay, RenderDocument, RenderFinalPage, RenderFinalSection
from itinerary_generation.editor_page_contract import final_section_page_id, ordered_page_ids, stable_page_id
from pdf_exporter_modules.day_page_guard import measure_day_story, one_page_day_flowable
from pdf_exporter_modules.image_constants import PDF_IMAGE_BOTTOM_Y, PDF_IMAGE_GAP, PDF_IMAGE_HALF_OFFSET, PDF_MIN_IMAGE_HEIGHT
from pdf_exporter_modules.image_flowables import FullPageBackgroundImage, FullPageTint, SamePageDayImage
from pdf_exporter_modules.image_layout import normalize_crop_focus
from pdf_exporter_modules.render_flowables import add_premium_rule, boxed_story_table
from pdf_exporter_modules.html_utils import clean_text, para_text
from pdf_exporter_modules.cover_page import CoverPageContent, normalize_cover_route_text, render_cover_content
from pdf_exporter_modules.render_content import render_content_blocks
from pdf_exporter_modules.render_text import li_text_with_line_breaks
from pdf_exporter_modules.story import add_bullets, add_paragraph, make_table
from pdf_exporter_modules import styles as pdf_styles
from pdf_exporter_modules.styles import apply_pdf_palette, make_styles, page_background
from pdf_exporter_modules.export_profiles import DEFAULT_PDF_EXPORT_PROFILE, resolve_pdf_export_profile
from ui.premium_final_notes import premium_note_cards


_SUPPORTED_FINAL_HTML_TAGS = {
    "b",
    "br",
    "div",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "span",
    "strong",
    "ul",
}

_SUPPORTED_FINAL_HTML_CLASSES = {
    "activity-inclusion-block",
    "activity-inclusion-title",
    "body-text",
    "content-block",
    "final-list",
    "inclusion-category-block",
    "inclusion-entry-detail",
    "inclusion-entry-spacer",
    "inclusion-entry-title",
    "section-title",
    "strong-line",
    "premium-linked-transfers",
    "premium-note-card",
    "premium-note-card-title",
    "premium-notes-grid",
    "premium-route-ribbon",
    "premium-travel-badge",
    "premium-travel-badges",
    "premium-travel-card",
    "premium-travel-chip",
    "premium-travel-chip-muted",
    "premium-travel-chips",
    "premium-travel-description",
    "premium-travel-kicker",
    "premium-travel-title",
    "premium-travel-timeline",
    "premium-travel-timeline-item",
}


def _iter_html_values(value):
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, Mapping):
                yield str(item.get("content_html") or item.get("html") or "")
            else:
                yield str(item or "")
        return
    if isinstance(value, Mapping):
        yield str(value.get("content_html") or value.get("html") or "")
        return
    yield str(value or "")


def _final_content_html_supported(html_fragment: str) -> bool:
    """Return True when an edited final-page fragment can render in typed PDF.

    This deliberately supports only the small, sanitized HTML contract emitted by
    the visual editor/final-page builders. Unsupported structures still use the
    legacy HTML exporter rather than silently dropping layout.
    """

    html_fragment = str(html_fragment or "").strip()
    if not html_fragment:
        return True

    soup = BeautifulSoup(html_fragment, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in _SUPPORTED_FINAL_HTML_TAGS:
            return False
        for class_name in tag.get("class") or []:
            if class_name not in _SUPPORTED_FINAL_HTML_CLASSES:
                return False
    return True


def _any_final_html_requires_fallback(value) -> bool:
    return any(
        bool(html.strip()) and not _final_content_html_supported(html)
        for html in _iter_html_values(value)
    )


def render_document_requires_html_fallback(render_document: RenderDocument | None, output_edits: Mapping | None = None) -> bool:
    """Return True only when unsupported saved HTML still owns visible content.

    Final-page HTML from the controlled editor contract can now render inside the
    typed PDF path. Day body HTML still falls back because it can contain complex
    arbitrary layout that has not yet been normalized into typed blocks.
    """

    if render_document is None:
        return True

    for section in getattr(render_document, "final_sections", []) or []:
        if _any_final_html_requires_fallback(getattr(section, "content_html", "")):
            return True
        for page in getattr(section, "pages", []) or []:
            if _any_final_html_requires_fallback(getattr(page, "content_html", "")):
                return True

    edits = output_edits or {}
    for day_edit in (edits.get("days") or {}).values() if isinstance(edits, Mapping) else []:
        if isinstance(day_edit, Mapping) and "blocks_html" in day_edit:
            return True

    draft = edits.get("editor_draft") if isinstance(edits, Mapping) else None
    if isinstance(draft, Mapping):
        for day in draft.get("days") or []:
            if not isinstance(day, Mapping):
                continue
            for block in day.get("blocks") or []:
                if isinstance(block, Mapping) and str(block.get("content_html") or block.get("html") or "").strip():
                    return True
        for section in draft.get("final_sections") or []:
            if not isinstance(section, Mapping):
                continue
            if _any_final_html_requires_fallback(section.get("content_html", "")):
                return True
            for page in section.get("pages") or []:
                if isinstance(page, Mapping) and _any_final_html_requires_fallback(page):
                    return True

    if not isinstance(edits, Mapping):
        return False
    legacy_html_keys = (
        "whats_included_pages_html",
        "whats_included_html",
        "whats_not_included_html",
    )
    return any(_any_final_html_requires_fallback(edits.get(key)) for key in legacy_html_keys)




def _render_supported_final_html(html_fragment: str, story, styles) -> None:
    html_fragment = str(html_fragment or "").strip()
    if not html_fragment:
        return

    soup = BeautifulSoup(html_fragment, "html.parser")

    def render_children(container):
        for child in getattr(container, "contents", []):
            if isinstance(child, NavigableString):
                text = clean_text(str(child))
                if text:
                    add_paragraph(story, text, styles["body"])
                continue
            if not getattr(child, "name", None):
                continue

            classes = child.get("class") or []
            if "content-block" in classes or "activity-inclusion-block" in classes:
                render_content_blocks(BeautifulSoup(str(child), "html.parser"), story, styles)
                continue

            if child.name in {"ul", "ol"}:
                add_bullets(story, [li_text_with_line_breaks(li) for li in child.find_all("li", recursive=False)], styles)
                continue

            if "section-title" in classes:
                add_paragraph(story, child.get_text(" "), styles["section"])
                continue

            if child.name in {"strong", "b"}:
                add_paragraph(story, child.get_text(" "), styles["body_bold"])
                continue

            if child.name in {"p", "span", "div", "em", "i"}:
                nested_structures = child.find_all(["ul", "ol"], recursive=False) or child.find_all(class_="content-block", recursive=False)
                if nested_structures:
                    render_children(child)
                    continue
                text = clean_text(child.get_text(" "))
                if text:
                    style_name = "body_bold" if "strong-line" in classes else "body"
                    add_paragraph(story, text, styles[style_name])

    render_children(soup)


def _cover_content(render_document: RenderDocument) -> CoverPageContent:
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


def _render_cover(render_document: RenderDocument, story, styles, temp_dir):
    render_cover_content(_cover_content(render_document), story, styles, temp_dir=temp_dir)


def _render_summary(render_document: RenderDocument, story, styles, temp_dir):
    summary = render_document.summary
    if not summary:
        return
    background_path = Path(str(getattr(summary, "background_path", "") or ""))
    if background_path.exists() and background_path.is_file():
        story.append(FullPageBackgroundImage(background_path, temp_dir, crop_focus=getattr(summary, "crop_focus", "top")))
        story.append(FullPageTint(color=pdf_styles.PAGE_BACKGROUND, alpha=0.38))

    glance_story = []
    add_paragraph(glance_story, getattr(summary, "trip_glance_title", "") or "Your Trip at a Glance", styles["page_title"], spacer_after=6)
    rows = []
    for line in getattr(summary, "trip_glance", []) or []:
        if line.label and line.value:
            rows.append([Paragraph(para_text(line.label), styles["table_header"]), Paragraph(para_text(str(line.value)), styles["table_cell"])])
    if rows:
        glance_story.append(make_table(rows, [34 * mm, 104 * mm], styles))
    story.append(boxed_story_table(glance_story, background=pdf_styles.SUMMARY_CARD))
    story.append(Spacer(1, 16 * mm))

    journey_story = []
    add_paragraph(journey_story, getattr(summary, "journey_arc_title", "") or "Your Journey Arc", styles["page_title"], spacer_after=6)
    columns = getattr(summary, "journey_arc_columns", {}) or {}
    table_rows = [[Paragraph(para_text(str(columns.get("chapter") or "Chapter")), styles["table_header"]), Paragraph(para_text(str(columns.get("days") or "Days")), styles["table_header"]), Paragraph(para_text(str(columns.get("experience") or "What You’ll Experience")), styles["table_header"])]]
    for row in getattr(summary, "journey_arc", []) or []:
        table_rows.append([
            Paragraph(para_text(str(row.get("chapter", ""))), styles["table_cell"]),
            Paragraph(para_text(str(row.get("days", ""))), styles["table_cell"]),
            Paragraph(para_text(str(row.get("experience", ""))), styles["table_cell"]),
        ])
    if len(table_rows) > 1:
        journey_story.append(make_table(table_rows, [34 * mm, 16 * mm, 90 * mm], styles))
    story.append(boxed_story_table(journey_story, background=pdf_styles.SUMMARY_CARD))


def _ellipsize_text(value: str, limit: int) -> str:
    """Return a compact sentence-safe text fragment for overflow fallback."""

    text = clean_text(value)
    if not text or len(text) <= limit:
        return text
    sentence_match = re.match(r"^(.{40,}?[.!?])\s", text)
    if sentence_match and len(sentence_match.group(1)) <= limit:
        return sentence_match.group(1)
    trimmed = text[: max(0, limit - 1)].rsplit(" ", 1)[0].strip()
    return f"{trimmed}…" if trimmed else ""


def _compact_items(items, limit: int, item_limit: int) -> list[str]:
    compacted = []
    for item in list(items or [])[:limit]:
        compacted.append(_ellipsize_text(item, item_limit))
    return [item for item in compacted if item]



def _section_by_title(block: RenderBlock, title: str):
    target = str(title or "").strip().lower()
    for section in block.extra_sections or []:
        if str(section.title or "").strip().lower() == target:
            return section
    return None


def _render_premium_travel_block_story(block: RenderBlock, styles) -> list:
    block_story = []
    if block.section_title:
        add_paragraph(block_story, block.section_title, styles["section"])
    if block.title:
        add_paragraph(block_story, block.title, styles["activity_title"])
    if block.description:
        add_paragraph(block_story, block.description, styles["body"])
    for meta in block.meta or []:
        if meta.value:
            add_paragraph(block_story, f"{meta.label}: {meta.value}" if meta.label else str(meta.value), styles["editor_small_note"])

    route = _section_by_title(block, "Route")
    if route and route.items:
        add_paragraph(block_story, route.items[0], styles["body_bold"])

    timeline = _section_by_title(block, "Journey timeline") or _section_by_title(block, "Coordinated day flow")
    if timeline and timeline.items:
        add_paragraph(block_story, timeline.title, styles["section"])
        add_bullets(block_story, timeline.items, styles, spacer_after=5)

    highlights = _section_by_title(block, "Highlights")
    if highlights and highlights.items:
        add_paragraph(block_story, "Highlights: " + " · ".join(highlights.items), styles["editor_small_note"])

    inclusions = _section_by_title(block, "Included journey") or _section_by_title(block, "Cruise inclusions")
    if inclusions and inclusions.items:
        add_paragraph(block_story, inclusions.title, styles["section"])
        add_bullets(block_story, inclusions.items, styles, spacer_after=5)

    linked = _section_by_title(block, "Linked transfers")
    if linked and linked.items:
        add_paragraph(block_story, "Linked transfers", styles["section"])
        add_bullets(block_story, linked.items, styles, spacer_after=5)

    return [boxed_story_table(block_story, width=156 * mm, padding=8)] if block_story else []

def _block_story(block: RenderBlock, styles, *, compact_level: int = 0) -> list:
    """Build flowables for one block.

    Activity content is deliberately not wrapped as one KeepTogether here. The
    complete day page is measured and kept together at the page level instead;
    wrapping the activity alone is what caused activities to jump to a new blank
    continuation page.
    """

    if "premium-travel-card" in str(block.css_class or "").split():
        return _render_premium_travel_block_story(block, styles)

    block_story = []
    if block.section_title:
        add_paragraph(block_story, block.section_title, styles["section"])
    if block.title:
        add_paragraph(block_story, block.title, styles["activity_title"] if block.kind in {"activity", "group_tour_day"} else styles["body_bold"])
    for meta in block.meta:
        if meta.value:
            add_paragraph(block_story, f"{meta.label}: {meta.value}" if meta.label else str(meta.value), styles["body"])

    if block.kind in {"activity", "group_tour_day"}:
        includes = list(block.includes or [])
        description = block.description
        notable_sights = list(block.notable_sights or [])
        extra_sections = list(block.extra_sections or [])
        if compact_level >= 1:
            description = _ellipsize_text(description, 220)
            notable_sights = notable_sights[:6]
        if compact_level >= 2:
            includes = _compact_items(includes, 6, 95)
            notable_sights = notable_sights[:4]
            description = _ellipsize_text(description, 160)
        if compact_level >= 3:
            includes = _compact_items(includes, 5, 75)
            extra_sections = []
            description = _ellipsize_text(description, 115)
            notable_sights = []

        if includes:
            included_label = "Included on This Tour Day" if block.kind == "group_tour_day" else "Included With This Experience"
            add_paragraph(block_story, included_label, styles["section"])
            add_bullets(block_story, includes, styles)
        if description:
            add_paragraph(block_story, "Description", styles["section"])
            add_paragraph(block_story, description, styles["body"])
        if notable_sights:
            add_paragraph(block_story, "Notable Sights", styles["section"])
            add_bullets(block_story, notable_sights, styles)
        for section in extra_sections:
            if section.items:
                items = _compact_items(section.items, 5, 90) if compact_level >= 2 else section.items
                if items:
                    add_paragraph(block_story, section.title, styles["section"])
                    add_bullets(block_story, items, styles)
        return block_story

    if block.kind == "transport":
        if block.includes:
            add_paragraph(block_story, "Includes", styles["section"])
            add_bullets(block_story, block.includes, styles)
        if block.description:
            add_paragraph(block_story, _ellipsize_text(block.description, 180) if compact_level >= 3 else block.description, styles["body"])
    elif block.kind == "accommodation":
        for line in block.lines:
            add_paragraph(block_story, line, styles["body"])
    else:
        if block.lines:
            add_bullets(block_story, block.lines, styles)
        if block.description:
            add_paragraph(block_story, _ellipsize_text(block.description, 180) if compact_level >= 3 else block.description, styles["body"])

    for section in block.extra_sections:
        if section.items:
            items = _compact_items(section.items, 5, 90) if compact_level >= 2 else section.items
            if items:
                add_paragraph(block_story, section.title, styles["section"])
                add_bullets(block_story, items, styles)
    return block_story


def _image_path_from_match(image_match, temp_dir):
    """Resolve a PDF image source from the final preview image contract."""

    if not image_match or not temp_dir:
        return None
    path = Path(str(image_match.get("path", "") or ""))
    if path.exists() and path.is_file():
        return path
    data_uri = str(image_match.get("data_uri", "") or "").strip()
    match = re.match(r"^data:image/(?:jpeg|jpg|png|webp);base64,(.+)$", data_uri, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    temp_path = Path(temp_dir) / f"preview_contract_day_image_{abs(hash(data_uri)) % 10_000_000}.img"
    try:
        temp_path.write_bytes(base64.b64decode(match.group(1)))
        return temp_path
    except (OSError, ValueError):
        return None


def _day_label(day: RenderDay) -> str:
    kicker = f"DAY {day.number}"
    if day.city:
        kicker += f" ✦ {str(day.city).upper()}"
    if getattr(day, "date", ""):
        kicker += f" ✦ {day.date}"
    return kicker


def _day_image_has_layout_budget(story, doc) -> bool:
    result = measure_day_story(story, doc.width, doc.height, label="day image budget")
    text_bottom_y = float(doc.pagesize[1] - doc.topMargin) - result.used_height
    image_top_y = min(text_bottom_y - PDF_IMAGE_GAP, (float(doc.pagesize[1]) / 2.0) - PDF_IMAGE_HALF_OFFSET)
    return (image_top_y - PDF_IMAGE_BOTTOM_Y) >= PDF_MIN_IMAGE_HEIGHT


def _render_day_story(day: RenderDay, styles, *, compact_level: int = 0) -> list:
    story = []
    add_paragraph(story, _day_label(day), styles["day_kicker"])
    add_paragraph(story, day.title, styles["day_title"])
    if day.city:
        add_paragraph(story, day.city, styles["city"])
    intro = _ellipsize_text(day.intro, 185) if compact_level >= 2 else day.intro
    add_paragraph(story, intro, styles["intro"])

    for block in day.blocks or []:
        story.extend(_block_story(block, styles, compact_level=compact_level))
    return story


def _render_day_image_flowable(image_match, crop_focus, temp_dir, doc):
    if not (image_match and temp_dir and doc):
        return None
    path = _image_path_from_match(image_match, temp_dir)
    if not (path and path.exists() and path.is_file()):
        return None
    return SamePageDayImage(
        source_path=path,
        temp_dir=temp_dir,
        x=0,
        content_top_y=doc.pagesize[1] - doc.topMargin,
        content_width=doc.pagesize[0],
        content_height=doc.height,
        page_height=doc.pagesize[1],
        bottom_y=PDF_IMAGE_BOTTOM_Y,
        crop_focus=normalize_crop_focus(crop_focus),
    )


def _build_one_page_day_flowable(day: RenderDay, styles, *, image_match=None, crop_focus="top", temp_dir=None, doc=None, min_compact_level: int = 0):
    """Return a guarded one-page flowable for a day.

    Order of operations:
    1. render full text and keep the image only when it has real page budget;
    2. compact low-priority descriptive text if the day is too tall;
    3. fail explicitly instead of silently creating an unlabelled continuation.
    """

    image_flowable = _render_day_image_flowable(image_match, crop_focus, temp_dir, doc)
    last_story = []
    for compact_level in range(max(0, int(min_compact_level or 0)), 4):
        candidate = _render_day_story(day, styles, compact_level=compact_level)
        last_story = candidate
        if doc and image_flowable and _day_image_has_layout_budget(candidate, doc):
            candidate = [*candidate, image_flowable]
        result = measure_day_story(candidate, doc.width, doc.height, label=_day_label(day)) if doc else None
        if result is None or result.fits:
            return one_page_day_flowable(candidate, doc.width, doc.height, label=_day_label(day))

    # This raises PdfDayLayoutError with the measured final compact story.
    return one_page_day_flowable(last_story, doc.width, doc.height, label=_day_label(day))

def _render_final_page(title: str, page: RenderFinalPage, story, styles, *, continued=False):
    add_paragraph(story, title, styles["page_title"])
    add_premium_rule(story)
    if page.content_html:
        _render_supported_final_html(page.content_html, story, styles)
        return
    for section in page.sections or []:
        add_paragraph(story, section.title, styles["section"])
        add_bullets(story, section.items, styles)
    if page.items:
        add_bullets(story, page.items, styles)
    for paragraph in page.paragraphs or []:
        add_paragraph(story, paragraph, styles["body"])



def _render_important_notes_final_page(title: str, page: RenderFinalPage, story, styles):
    add_paragraph(story, title, styles["page_title"])
    add_premium_rule(story)
    cards = premium_note_cards(page.paragraphs or page.items or [])
    if not cards:
        for paragraph in page.paragraphs or []:
            add_paragraph(story, paragraph, styles["body"])
        return
    for card_title, body in cards:
        card_story = []
        add_paragraph(card_story, card_title, styles["section"])
        add_paragraph(card_story, body, styles["body"])
        story.append(KeepTogether([boxed_story_table(card_story, width=156 * mm, padding=7)]))
        story.append(Spacer(1, 5))

def _render_final_section(section: RenderFinalSection, story, styles):
    pages = list(section.pages or [])
    if not pages:
        pages = [RenderFinalPage(sections=list(section.sections or []), items=list(section.items or []), paragraphs=list(section.paragraphs or []))]
    for index, page in enumerate(pages):
        if index > 0:
            story.append(PageBreak())
        if str(section.section_id or "") == "important_travel_notes" and not page.content_html:
            _render_important_notes_final_page(section.title, page, story, styles)
        else:
            _render_final_page(section.title, page, story, styles, continued=index > 0)


def _render_internal_review_appendix(render_document: RenderDocument, story, styles):
    add_paragraph(story, "Internal Review Notes", styles["page_title"])
    add_premium_rule(story)
    day_count = len(render_document.days or [])
    final_count = len(render_document.final_sections or [])
    add_paragraph(story, f"Days: {day_count}", styles["body"])
    add_paragraph(story, f"Final sections: {final_count}", styles["body"])
    if render_document.route:
        add_paragraph(story, f"Route: {render_document.route}", styles["body"])
    add_paragraph(story, "Use this copy for internal review only. Confirm pictures, inclusions, exclusions, travel notes, and page breaks before sending the client PDF.", styles["editor_note"])


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
        title=profile.label,
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
            page_renderers.append(("summary", lambda: _render_summary(render_document, story, styles, image_temp_dir)))

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
