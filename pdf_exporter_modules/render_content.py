"""Public compatibility facade for PDF content rendering."""

import re

from text_polish import expand_time_with_duration
from visual_editor_component.style_presets import pdf_base_style_for_classes, pdf_effects_for_classes

from .html_utils import clean_text
from .render_content_blocks import render_content_blocks
from .render_inclusion_content import render_inclusion_category_block
from .render_pages import render_day_section_pdf, render_general_page


def _activity_time_range_text(time_text, duration_text):
    """PDF-side fallback: expand a clean start time and duration to a range."""
    cleaned_time = clean_text(time_text)
    base = re.sub(r"^time\s*:\s*", "", cleaned_time, flags=re.IGNORECASE).strip()
    expanded = expand_time_with_duration(base, duration_text)
    return f"Time: {expanded}" if expanded and expanded != base else cleaned_time


__all__ = ["render_content_blocks", "render_day_section_pdf", "render_general_page", "render_inclusion_category_block"]
