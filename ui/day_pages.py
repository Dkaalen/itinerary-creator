"""Backward-compatible facade for A4 day/final page rendering helpers."""

from __future__ import annotations

from ui.day_page_sections import (
    render_day_page,
    render_day_pages,
    render_day_section,
    render_day_visual_block,
)
from ui.final_list_pages import render_split_list_pages
from ui.inclusion_pages import render_categorized_inclusions_pages, render_inclusion_sections_inner_html, render_inclusion_page_inner_htmls
from ui.custom_final_pages import render_custom_html_final_page, render_custom_html_final_pages, render_text_paragraph_page
