"""Render complete day and general HTML pages to PDF stories."""

from .day_images import add_day_image_if_possible
from .render_content_blocks import render_content_blocks
from .render_controlled_content import add_controlled_list
from .render_flowables import add_premium_rule
from .story import add_paragraph


def render_day_section_pdf(section, story, styles):
    kicker = section.select_one(".day-kicker")
    if kicker: add_paragraph(story, kicker.get_text(" "), styles["day_kicker"])
    else:
        label = section.select_one(".day-label")
        if label and "day-label-legacy" not in (label.get("class") or []): add_paragraph(story, label.get_text(" "), styles["day_label"])
    selectors = [(".day-title", "day_title"), (".intro", "intro")]
    for selector, style_name in selectors:
        tag = section.select_one(selector)
        if tag: add_paragraph(story, tag.get_text(" "), styles[style_name])
    render_content_blocks(section, story, styles)


def _add_day_image(page, story, styles, *, html_path, temp_dir, available_width, available_height, page_story_start, left_margin, top_margin):
    if "day-page" not in (page.get("class") or []) or not all((html_path, temp_dir, available_width, available_height)): return
    add_day_image_if_possible(page, story, html_path, temp_dir, available_width, available_height, measurement_story=story[page_story_start:], left_margin=left_margin, top_margin=top_margin)


def render_general_page(page, story, styles, html_path=None, temp_dir=None, available_width=None, available_height=None, left_margin=0, top_margin=0):
    start = len(story)
    day_sections = [child for child in page.find_all(recursive=False) if "day-section" in (child.get("class") or [])]
    if day_sections:
        for section in day_sections: render_day_section_pdf(section, story, styles)
        _add_day_image(page, story, styles, html_path=html_path, temp_dir=temp_dir, available_width=available_width, available_height=available_height, page_story_start=start, left_margin=left_margin, top_margin=top_margin)
        return
    for selector, style_name in ((".final-page-title", "page_title"), (".day-label", "day_label"), (".day-title", "day_title"), (".intro", "intro")):
        tag = page.select_one(selector)
        if tag:
            add_paragraph(story, tag.get_text(" "), styles[style_name])
            if selector == ".final-page-title": add_premium_rule(story)
    render_content_blocks(page, story, styles)
    for item in page.find_all("ul", recursive=False): add_controlled_list(story, item, styles)
    _add_day_image(page, story, styles, html_path=html_path, temp_dir=temp_dir, available_width=available_width, available_height=available_height, page_story_start=start, left_margin=left_margin, top_margin=top_margin)
