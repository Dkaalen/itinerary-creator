"""Custom final-page rendering helpers."""

from __future__ import annotations

from text_polish import polish_client_text
from ui.editor_sanitizer import clean_visual_editor_html
from ui.render_helpers import esc, normalize_list


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
        continued = "" if index == 0 else " continued"
        html_text += f'<div class="a4-page {esc(page_class)}"><div class="final-page-title">{esc(title)}{continued}</div>{inner_html}</div>'
    return html_text


def render_text_paragraph_page(title, paragraphs):
    clean_paragraphs = [polish_client_text(item) for item in normalize_list(paragraphs) if polish_client_text(item)]
    if not clean_paragraphs:
        return ""

    html_text = (
        f'<div class="a4-page final-list-page important-notes-page">'
        f'<div class="final-page-title">{esc(title)}</div>'
        f'<div class="content-block notes-block">'
    )
    for paragraph in clean_paragraphs:
        html_text += f'<div class="body-text note-paragraph">{esc(paragraph)}</div>'
    html_text += "</div></div>"
    return html_text
