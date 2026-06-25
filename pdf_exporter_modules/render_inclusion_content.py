"""Render inclusion-category HTML with item-level pagination safety."""

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether

from .render_controlled_content import add_controlled_list, add_controlled_paragraph, has_controlled_classes, is_divider, render_controlled_note_block
from .render_flowables import add_premium_rule


def _append_entry(story, entry_story):
    if entry_story: story.append(KeepTogether(entry_story))


def _is_renderable(element) -> bool:
    classes = set(element.get("class") or [])
    return bool(is_divider(element) or "ve-note-block" in classes or "section-title" in classes or "inclusion-entry-title" in classes or "inclusion-entry-detail" in classes or "inclusion-entry-spacer" in classes or element.name == "ul" or "body-text" in classes or has_controlled_classes(element))


def render_inclusion_category_block(child, story, styles):
    entry_story = []
    elements = list(child.find_all(recursive=False))
    for index, element in enumerate(elements):
        classes = set(element.get("class") or [])
        if is_divider(element):
            _append_entry(story, entry_story); entry_story = []; add_premium_rule(story, width=38 * mm, space_after=8)
        elif "ve-note-block" in classes:
            _append_entry(story, entry_story); entry_story = []; render_controlled_note_block(element, story, styles)
        elif "section-title" in classes:
            _append_entry(story, entry_story); entry_story = []; add_controlled_paragraph(story, element, styles, "section")
        elif "inclusion-entry-title" in classes:
            _append_entry(story, entry_story); entry_story = []; add_controlled_paragraph(entry_story, element, styles, "body_bold")
        elif "inclusion-entry-detail" in classes: add_controlled_paragraph(entry_story, element, styles, "body")
        elif "inclusion-entry-spacer" in classes: _append_entry(story, entry_story); entry_story = []
        elif element.name == "ul":
            _append_entry(story, entry_story); entry_story = []
            add_controlled_list(story, element, styles, spacer_after=7 if any(_is_renderable(candidate) for candidate in elements[index + 1:]) else 0)
        elif "body-text" in classes or has_controlled_classes(element):
            add_controlled_paragraph(entry_story or story, element, styles, "body_bold" if "strong-line" in classes else "body")
    _append_entry(story, entry_story)
