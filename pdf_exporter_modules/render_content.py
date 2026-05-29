"""General page/day/content block PDF rendering."""

import re

from reportlab.platypus import KeepTogether

from text_polish import expand_time_with_duration

from .day_images import add_day_image_if_possible
from .html_utils import clean_text
from .render_flowables import add_premium_rule
from .render_text import li_text_with_line_breaks
from .story import add_bullets, add_paragraph


def _activity_time_range_text(time_text, duration_text):
    """PDF-side fallback: expand clean single start time + duration to a range."""
    cleaned_time = clean_text(time_text)
    base = re.sub(r"^time\s*:\s*", "", cleaned_time, flags=re.IGNORECASE).strip()
    expanded = expand_time_with_duration(base, duration_text)
    if expanded and expanded != base:
        return f"Time: {expanded}"
    return cleaned_time


def render_content_blocks(container, story, styles):
    for child in container.find_all(recursive=False):
        classes = child.get("class") or []
        if "content-block" in classes or "activity-inclusion-block" in classes:
            block_story = []

            duration_meta_text = ""
            if "activity-block" in classes:
                for possible_meta in child.find_all(recursive=False):
                    meta_text = clean_text(possible_meta.get_text(" "))
                    if re.match(r"^(?:duration|ferry duration|cruise duration)\s*:", meta_text, flags=re.IGNORECASE):
                        duration_meta_text = meta_text
                        break

            for element in child.find_all(recursive=False):
                element_classes = element.get("class") or []

                if "section-title" in element_classes:
                    add_paragraph(block_story, element.get_text(" "), styles["section"])
                elif "activity-inclusion-title" in element_classes:
                    add_paragraph(block_story, element.get_text(" "), styles["activity_title"])
                elif element.name == "ul":
                    add_bullets(block_story, [li_text_with_line_breaks(li) for li in element.find_all("li", recursive=False)], styles)
                elif "body-text" in element_classes:
                    text = clean_text(element.get_text(" "))
                    if "activity-block" in classes and re.match(r"^time\s*:", text, flags=re.IGNORECASE):
                        text = _activity_time_range_text(text, duration_meta_text)
                    if "strong-line" in element_classes:
                        add_paragraph(block_story, text, styles["body_bold"])
                    else:
                        add_paragraph(block_story, text, styles["body"])

            if "activity-block" in classes and block_story:
                story.append(KeepTogether(block_story))
            else:
                story.extend(block_story)


def render_day_section_pdf(section, story, styles):
    kicker = section.select_one(".day-kicker")
    if kicker:
        add_paragraph(story, kicker.get_text(" "), styles["day_kicker"])
    else:
        label = section.select_one(".day-label")
        if label and "day-label-legacy" not in (label.get("class") or []):
            add_paragraph(story, label.get_text(" "), styles["day_label"])

    selector_styles = [(".day-title", "day_title"), (".intro", "intro")]
    if not kicker:
        selector_styles.insert(1, (".city", "city"))

    for selector, style_name in selector_styles:
        tag = section.select_one(selector)
        if tag:
            add_paragraph(story, tag.get_text(" "), styles[style_name])

    render_content_blocks(section, story, styles)


def render_general_page(
    page,
    story,
    styles,
    html_path=None,
    temp_dir=None,
    available_width=None,
    available_height=None,
    left_margin=0,
    top_margin=0,
):
    page_story_start = len(story)

    day_sections = [child for child in page.find_all(recursive=False) if "day-section" in (child.get("class") or [])]
    if day_sections:
        for index, section in enumerate(day_sections):
            render_day_section_pdf(section, story, styles)
        if "day-page" in (page.get("class") or []) and html_path and temp_dir and available_width and available_height:
            add_day_image_if_possible(
                page,
                story,
                html_path,
                temp_dir,
                available_width,
                available_height,
                measurement_story=story[page_story_start:],
                left_margin=left_margin,
                top_margin=top_margin,
            )
        return

    for selector, style_name in [
        (".final-page-title", "page_title"),
        (".day-label", "day_label"),
        (".day-title", "day_title"),
        (".city", "city"),
        (".intro", "intro"),
    ]:
        tag = page.select_one(selector)
        if tag:
            add_paragraph(story, tag.get_text(" "), styles[style_name])
            if selector == ".final-page-title":
                add_premium_rule(story)

    render_content_blocks(page, story, styles)

    for ul in page.find_all("ul", recursive=False):
        add_bullets(story, [li_text_with_line_breaks(li) for li in ul.find_all("li", recursive=False)], styles)

    if "day-page" in (page.get("class") or []) and html_path and temp_dir and available_width and available_height:
        add_day_image_if_possible(
            page,
            story,
            html_path,
            temp_dir,
            available_width,
            available_height,
            measurement_story=story[page_story_start:],
            left_margin=left_margin,
            top_margin=top_margin,
        )
