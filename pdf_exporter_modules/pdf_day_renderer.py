"""Day-page rendering for typed PDF export."""

from __future__ import annotations

import re

from pdf_exporter_modules.day_page_guard import measure_day_story, one_page_day_flowable
from pdf_exporter_modules.html_utils import clean_text
from pdf_exporter_modules.image_constants import PDF_IMAGE_BOTTOM_Y, PDF_IMAGE_GAP, PDF_IMAGE_HALF_OFFSET, PDF_MIN_IMAGE_HEIGHT
from pdf_exporter_modules.pdf_image_renderer import render_day_image_flowable
from pdf_exporter_modules.story import add_bullets, add_paragraph
from itinerary_generation.render_model import RenderBlock, RenderDay


def ellipsize_text(value: str, limit: int) -> str:
    """Return a compact sentence-safe text fragment for overflow fallback."""

    text = clean_text(value)
    if not text or len(text) <= limit:
        return text
    sentence_match = re.match(r"^(.{40,}?[.!?])\s", text)
    if sentence_match and len(sentence_match.group(1)) <= limit:
        return sentence_match.group(1)
    trimmed = text[: max(0, limit - 1)].rsplit(" ", 1)[0].strip()
    return f"{trimmed}…" if trimmed else ""


def compact_items(items, limit: int, item_limit: int) -> list[str]:
    compacted = []
    for item in list(items or [])[:limit]:
        compacted.append(ellipsize_text(item, item_limit))
    return [item for item in compacted if item]


def block_story(block: RenderBlock, styles, *, compact_level: int = 0) -> list:
    """Build flowables for one block."""

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
            description = ellipsize_text(description, 220)
            notable_sights = notable_sights[:6]
        if compact_level >= 2:
            includes = compact_items(includes, 6, 95)
            notable_sights = notable_sights[:4]
            description = ellipsize_text(description, 160)
        if compact_level >= 3:
            includes = compact_items(includes, 5, 75)
            extra_sections = []
            description = ellipsize_text(description, 115)
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
                items = compact_items(section.items, 5, 90) if compact_level >= 2 else section.items
                if items:
                    add_paragraph(block_story, section.title, styles["section"])
                    add_bullets(block_story, items, styles)
        return block_story

    if block.kind == "transport":
        if block.includes:
            add_paragraph(block_story, "Includes", styles["section"])
            add_bullets(block_story, block.includes, styles)
        if block.description:
            add_paragraph(block_story, ellipsize_text(block.description, 180) if compact_level >= 3 else block.description, styles["body"])
    elif block.kind == "accommodation":
        for line in block.lines:
            add_paragraph(block_story, line, styles["body"])
    else:
        if block.lines:
            add_bullets(block_story, block.lines, styles)
        if block.description:
            add_paragraph(block_story, ellipsize_text(block.description, 180) if compact_level >= 3 else block.description, styles["body"])

    for section in block.extra_sections:
        if section.items:
            items = compact_items(section.items, 5, 90) if compact_level >= 2 else section.items
            if items:
                add_paragraph(block_story, section.title, styles["section"])
                add_bullets(block_story, items, styles)
    return block_story


def day_label(day: RenderDay) -> str:
    kicker = f"DAY {day.number}"
    if day.city:
        kicker += f" ✦ {str(day.city).upper()}"
    if getattr(day, "date", ""):
        kicker += f" ✦ {day.date}"
    return kicker


def day_image_has_layout_budget(story, doc) -> bool:
    result = measure_day_story(story, doc.width, doc.height, label="day image budget")
    text_bottom_y = float(doc.pagesize[1] - doc.topMargin) - result.used_height
    image_top_y = min(text_bottom_y - PDF_IMAGE_GAP, (float(doc.pagesize[1]) / 2.0) - PDF_IMAGE_HALF_OFFSET)
    return (image_top_y - PDF_IMAGE_BOTTOM_Y) >= PDF_MIN_IMAGE_HEIGHT


def render_day_story(day: RenderDay, styles, *, compact_level: int = 0) -> list:
    story = []
    add_paragraph(story, day_label(day), styles["day_kicker"])
    add_paragraph(story, day.title, styles["day_title"])
    if day.city:
        add_paragraph(story, day.city, styles["city"])
    intro = ellipsize_text(day.intro, 185) if compact_level >= 2 else day.intro
    add_paragraph(story, intro, styles["intro"])

    for block in day.blocks or []:
        story.extend(block_story(block, styles, compact_level=compact_level))
    return story


def build_one_page_day_flowable(day: RenderDay, styles, *, image_match=None, crop_focus="top", temp_dir=None, doc=None, min_compact_level: int = 0):
    """Return a guarded one-page flowable for a day."""

    image_flowable = render_day_image_flowable(image_match, crop_focus, temp_dir, doc)
    last_story = []
    for compact_level in range(max(0, int(min_compact_level or 0)), 4):
        candidate = render_day_story(day, styles, compact_level=compact_level)
        last_story = candidate
        if doc and image_flowable and day_image_has_layout_budget(candidate, doc):
            candidate = [*candidate, image_flowable]
        result = measure_day_story(candidate, doc.width, doc.height, label=day_label(day)) if doc else None
        if result is None or result.fits:
            return one_page_day_flowable(candidate, doc.width, doc.height, label=day_label(day))

    return one_page_day_flowable(last_story, doc.width, doc.height, label=day_label(day))
