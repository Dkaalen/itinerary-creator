"""Custom final-page rendering helpers."""

from __future__ import annotations

from text_polish import polish_client_text
from ui.editor_sanitizer import clean_visual_editor_html
from ui.render_helpers import esc, normalize_list
from ui.premium_final_notes import render_premium_notes_inner_html


def render_custom_html_final_page(title, inner_html, page_class="final-list-page"):
    inner_html = clean_visual_editor_html(inner_html or "")
    if not inner_html:
        return ""
    return f'<div class="a4-page {esc(page_class)}"><div class="final-page-title">{esc(title)}</div>{inner_html}</div>'


def render_custom_html_final_pages(title, page_htmls, page_class="final-list-page"):
    """Render saved visual-editor final pages without flattening them."""

    if not isinstance(page_htmls, list):
        page_htmls = [page_htmls]
    html_text = ""
    for index, inner_html in enumerate(page_htmls):
        inner_html = clean_visual_editor_html(inner_html or "")
        if not inner_html:
            continue
        html_text += f'<div class="a4-page {esc(page_class)}"><div class="final-page-title">{esc(title)}</div>{inner_html}</div>'
    return html_text


def render_text_paragraph_page(title, paragraphs):
    clean_paragraphs = [polish_client_text(item) for item in normalize_list(paragraphs) if polish_client_text(item)]
    if not clean_paragraphs:
        return ""

    inner_html = render_premium_notes_inner_html(clean_paragraphs)
    if not inner_html:
        inner_html = '<div class="content-block notes-block">'
        for paragraph in clean_paragraphs:
            inner_html += f'<div class="body-text note-paragraph">{esc(paragraph)}</div>'
        inner_html += "</div>"

    return (
        f'<div class="a4-page final-list-page important-notes-page premium-notes-page">'
        f'<div class="final-page-title">{esc(title)}</div>'
        f'{inner_html}'
        f'</div>'
    )
