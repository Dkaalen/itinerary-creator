"""Render generic PDF content blocks by delegating controlled block types."""

from .render_controlled_content import add_controlled_list, add_controlled_paragraph, has_controlled_classes, is_divider, render_controlled_note_block, render_divider
from .render_inclusion_content import render_inclusion_category_block


def render_content_blocks(container, story, styles):
    for child in container.find_all(recursive=False):
        classes = set(child.get("class") or [])
        if is_divider(child): render_divider(story); continue
        if "ve-note-block" in classes: render_controlled_note_block(child, story, styles); continue
        if not ({"content-block", "activity-inclusion-block"} & classes): continue
        if "inclusion-category-block" in classes: render_inclusion_category_block(child, story, styles); continue
        block_story = []
        for element in child.find_all(recursive=False):
            element_classes = set(element.get("class") or [])
            if is_divider(element): render_divider(block_story)
            elif "ve-note-block" in element_classes: render_controlled_note_block(element, block_story, styles)
            elif "section-title" in element_classes: add_controlled_paragraph(block_story, element, styles, "section")
            elif "premium-note-card" in element_classes:
                for nested in element.find_all(recursive=False):
                    nested_classes = set(nested.get("class") or [])
                    if "premium-note-card-title" in nested_classes: add_controlled_paragraph(block_story, nested, styles, "section")
                    elif "body-text" in nested_classes: add_controlled_paragraph(block_story, nested, styles, "body")
            elif "activity-inclusion-title" in element_classes: add_controlled_paragraph(block_story, element, styles, "activity_title")
            elif element.name == "ul": add_controlled_list(block_story, element, styles)
            elif "body-text" in element_classes or has_controlled_classes(element): add_controlled_paragraph(block_story, element, styles, "body_bold" if "strong-line" in element_classes else "body")
        story.extend(block_story)
