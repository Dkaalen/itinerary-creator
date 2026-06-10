"""General page/day/content block PDF rendering."""

import re

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether

from text_polish import expand_time_with_duration

from . import styles as pdf_styles
from .day_images import add_day_image_if_possible
from .html_utils import clean_text
from .render_flowables import add_premium_rule
from .render_text import li_text_with_line_breaks
from .story import add_bullets, add_paragraph


CONTROLLED_TEXT_CLASSES = {
    "ve-text-small-note",
    "ve-text-large",
    "ve-text-heading",
    "ve-text-subheading",
    "ve-text-muted",
    "ve-text-accent",
}
CONTROLLED_COLOR_CLASSES = {
    "ve-color-muted",
    "ve-color-accent",
    "ve-color-warning",
    "ve-color-highlight",
}
CONTROLLED_SPACING_CLASSES = {"ve-spacing-compact", "ve-spacing-normal"}
CONTROLLED_CLASSES = CONTROLLED_TEXT_CLASSES | CONTROLLED_COLOR_CLASSES | CONTROLLED_SPACING_CLASSES


def _activity_time_range_text(time_text, duration_text):
    """PDF-side fallback: expand clean single start time + duration to a range."""
    cleaned_time = clean_text(time_text)
    base = re.sub(r"^time\s*:\s*", "", cleaned_time, flags=re.IGNORECASE).strip()
    expanded = expand_time_with_duration(base, duration_text)
    if expanded and expanded != base:
        return f"Time: {expanded}"
    return cleaned_time


def _append_inclusion_entry(story, entry_story):
    if entry_story:
        story.append(KeepTogether(entry_story))


def _class_set(element) -> set[str]:
    return {str(cls) for cls in (element.get("class") or [])}


def _controlled_style(styles, classes, default_style_name="body"):
    base_name = default_style_name
    if "ve-text-small-note" in classes:
        base_name = "editor_small_note"
    elif "ve-text-large" in classes:
        base_name = "editor_large"
    elif "ve-text-heading" in classes:
        base_name = "editor_heading"
    elif "ve-text-subheading" in classes:
        base_name = "editor_subheading"

    style = styles[base_name]
    text_color = None
    back_color = None
    suffix = []

    if "ve-text-muted" in classes or "ve-color-muted" in classes:
        text_color = pdf_styles.MUTED
        suffix.append("muted")
    if "ve-text-accent" in classes:
        text_color = pdf_styles.ACCENT
        suffix.append("accent")
    if "ve-color-accent" in classes:
        text_color = colors.HexColor("#9a6a16")
        suffix.append("gold")
    if "ve-color-warning" in classes:
        text_color = colors.HexColor("#7a1c1c")
        suffix.append("warning")
    if "ve-color-highlight" in classes:
        back_color = colors.HexColor("#eadfcf")
        suffix.append("highlight")

    space_after = None
    if "ve-spacing-compact" in classes:
        space_after = 1.5
        suffix.append("compact")
    elif "ve-spacing-normal" in classes:
        space_after = 6
        suffix.append("normal")

    if not suffix:
        return style

    kwargs = {
        "parent": style,
        "textColor": text_color or getattr(style, "textColor", pdf_styles.BODY),
    }
    if back_color is not None:
        kwargs["backColor"] = back_color
    if space_after is not None:
        kwargs["spaceAfter"] = space_after
    return ParagraphStyle(f"{style.name}_{'_'.join(suffix)}", **kwargs)


def _add_controlled_paragraph(story, element, styles, default_style_name="body"):
    text = clean_text(element.get_text(" "))
    if not text:
        return
    classes = _class_set(element)
    add_paragraph(story, text, _controlled_style(styles, classes, default_style_name))


def _is_divider(element) -> bool:
    classes = _class_set(element)
    return "ve-divider" in classes or "ve-divider-block" in classes


def _has_controlled_classes(element) -> bool:
    return bool(_class_set(element) & CONTROLLED_CLASSES)


def _add_controlled_list(story, ul, styles):
    items = ul.find_all("li", recursive=False)
    if not items:
        return
    if not any(_has_controlled_classes(li) for li in items):
        add_bullets(story, [li_text_with_line_breaks(li) for li in items], styles)
        return
    for li in items:
        text = li_text_with_line_breaks(li)
        if not text:
            continue
        classes = _class_set(li)
        add_paragraph(story, f"• {text}", _controlled_style(styles, classes, "bullet"))


def _render_controlled_note_block(child, story, styles):
    note_story = []
    for element in child.find_all(recursive=False):
        if _is_divider(element):
            continue
        if element.name == "ul":
            _add_controlled_list(note_story, element, styles)
            continue
        _add_controlled_paragraph(note_story, element, styles, "editor_note")
    if not note_story:
        text = clean_text(child.get_text(" "))
        if text:
            add_paragraph(note_story, text, styles["editor_note"])
    if note_story:
        story.append(KeepTogether(note_story))


def render_inclusion_category_block(child, story, styles):
    """Render edited/generated inclusion HTML with item-level keep-together."""

    entry_story = []
    for element in child.find_all(recursive=False):
        element_classes = element.get("class") or []
        classes = set(element_classes)

        if _is_divider(element):
            _append_inclusion_entry(story, entry_story)
            entry_story = []
            add_premium_rule(story, width=38 * mm, space_after=8)
        elif "ve-note-block" in classes:
            _append_inclusion_entry(story, entry_story)
            entry_story = []
            _render_controlled_note_block(element, story, styles)
        elif "section-title" in element_classes:
            _append_inclusion_entry(story, entry_story)
            entry_story = []
            _add_controlled_paragraph(story, element, styles, "section")
        elif "inclusion-entry-title" in element_classes:
            _append_inclusion_entry(story, entry_story)
            entry_story = []
            _add_controlled_paragraph(entry_story, element, styles, "body_bold")
        elif "inclusion-entry-detail" in element_classes:
            _add_controlled_paragraph(entry_story, element, styles, "body")
        elif "inclusion-entry-spacer" in element_classes:
            _append_inclusion_entry(story, entry_story)
            entry_story = []
        elif element.name == "ul":
            _append_inclusion_entry(story, entry_story)
            entry_story = []
            _add_controlled_list(story, element, styles)
        elif "body-text" in element_classes or _has_controlled_classes(element):
            target_story = entry_story or story
            default_style = "body_bold" if "strong-line" in element_classes else "body"
            _add_controlled_paragraph(target_story, element, styles, default_style)

    _append_inclusion_entry(story, entry_story)


def render_content_blocks(container, story, styles):
    for child in container.find_all(recursive=False):
        classes = child.get("class") or []
        class_set = set(classes)
        if _is_divider(child):
            add_premium_rule(story, width=38 * mm, space_after=8)
            continue
        if "ve-note-block" in class_set:
            _render_controlled_note_block(child, story, styles)
            continue
        if "content-block" in classes or "activity-inclusion-block" in classes:
            if "inclusion-category-block" in classes:
                render_inclusion_category_block(child, story, styles)
                continue

            block_story = []

            if "ve-divider-block" in class_set:
                add_premium_rule(story, width=38 * mm, space_after=8)
                continue
            if "ve-note-block" in class_set:
                _render_controlled_note_block(child, story, styles)
                continue

            for element in child.find_all(recursive=False):
                element_classes = element.get("class") or []
                element_class_set = set(element_classes)

                if _is_divider(element):
                    add_premium_rule(block_story, width=38 * mm, space_after=8)
                elif "ve-note-block" in element_class_set:
                    _render_controlled_note_block(element, block_story, styles)
                elif "section-title" in element_classes:
                    _add_controlled_paragraph(block_story, element, styles, "section")
                elif "activity-inclusion-title" in element_classes:
                    _add_controlled_paragraph(block_story, element, styles, "activity_title")
                elif element.name == "ul":
                    _add_controlled_list(block_story, element, styles)
                elif "body-text" in element_classes or _has_controlled_classes(element):
                    default_style = "body_bold" if "strong-line" in element_classes else "body"
                    _add_controlled_paragraph(block_story, element, styles, default_style)

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
        _add_controlled_list(story, ul, styles)

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
