"""HTML renderer for typed final-section render documents.

Final-page content is resolved before rendering and stored on
``RenderDocument.final_sections``.  This module keeps the preview path from
repeating the same ownership/fallback decisions as the PDF path.
"""

from __future__ import annotations

from collections.abc import Iterable

from itinerary_generation.editor_page_contract import final_section_page_id
from itinerary_generation.render_model import RenderFinalPage, RenderFinalSection
from text_polish import polish_client_text
from ui.editor_sanitizer import clean_visual_editor_html
from ui.inclusion_pages import render_inclusion_sections_inner_html
from ui.premium_final_notes import render_premium_notes_inner_html
from ui.render_helpers import esc, normalize_list, render_list_items


def _page_class(section: RenderFinalSection) -> str:
    classes = ["final-list-page"]
    extra = str(getattr(section, "css_class", "") or "").strip()
    if extra:
        classes.extend(part for part in extra.split() if part and part not in classes)
    if str(getattr(section, "section_id", "") or "") == "important_travel_notes" and "premium-notes-page" not in classes:
        classes.append("premium-notes-page")
    return " ".join(classes)


def _page_has_content(page: RenderFinalPage) -> bool:
    return bool(
        str(getattr(page, "content_html", "") or "").strip()
        or getattr(page, "sections", None)
        or getattr(page, "items", None)
        or getattr(page, "paragraphs", None)
    )


def render_final_page_inner_html(section: RenderFinalSection, page: RenderFinalPage) -> str:
    content_html = clean_visual_editor_html(getattr(page, "content_html", "") or "")
    if content_html:
        return content_html

    if str(getattr(section, "section_id", "") or "") == "important_travel_notes":
        paragraphs = [polish_client_text(item) for item in normalize_list(page.paragraphs or page.items) if polish_client_text(item)]
        premium_html = render_premium_notes_inner_html(paragraphs)
        if premium_html:
            return premium_html
        return "".join(f'<div class="body-text note-paragraph">{esc(paragraph)}</div>' for paragraph in paragraphs)

    html_text = ""
    if page.sections:
        html_text += render_inclusion_sections_inner_html(page.sections)
    if page.items:
        html_text += render_list_items(page.items, class_name="final-list")
    for paragraph in page.paragraphs or []:
        clean_paragraph = polish_client_text(paragraph)
        if clean_paragraph:
            html_text += f'<div class="body-text note-paragraph">{esc(clean_paragraph)}</div>'
    return html_text


def _page_inner_html(section: RenderFinalSection, page: RenderFinalPage) -> str:
    """Compatibility alias for older imports."""

    return render_final_page_inner_html(section, page)


def render_final_section_page_html(section: RenderFinalSection, page: RenderFinalPage, *, continued: bool = False) -> str:
    if not _page_has_content(page):
        return ""
    inner_html = render_final_page_inner_html(section, page)
    if not inner_html:
        return ""
    title = section.title
    return (
        f'<div class="a4-page {esc(_page_class(section))}">'
        f'<div class="final-page-title">{esc(title)}</div>'
        f'{inner_html}'
        f'</div>'
    )


def _section_pages(section: RenderFinalSection) -> list[RenderFinalPage]:
    pages = list(getattr(section, "pages", None) or [])
    if pages:
        return pages
    if section.content_html or section.sections or section.items or section.paragraphs:
        return [
            RenderFinalPage(
                content_html=str(section.content_html or ""),
                sections=list(section.sections or []),
                items=list(section.items or []),
                paragraphs=list(section.paragraphs or []),
            )
        ]
    return []


def final_section_preview_page_id(section: RenderFinalSection) -> str:
    """Return the same page id used by the typed PDF exporter."""

    section_id = str(getattr(section, "section_id", "") or "")
    if section_id in {"whats_included", "whats_not_included", "important_travel_notes"}:
        return final_section_page_id(section_id)
    return section_id


def render_final_section_html(section: RenderFinalSection) -> str:
    """Render one already-resolved final section for the HTML preview."""

    html_text = ""
    for index, page in enumerate(_section_pages(section)):
        html_text += render_final_section_page_html(section, page, continued=index > 0)
    return html_text


def render_final_sections_html_by_id(final_sections: Iterable[RenderFinalSection] | None) -> dict[str, str]:
    """Return final-section preview pages keyed by shared editor/PDF page id."""

    pages: dict[str, str] = {}
    for section in final_sections or []:
        html_text = render_final_section_html(section)
        if html_text:
            pages[final_section_preview_page_id(section)] = html_text
    return pages


def render_final_sections_html(final_sections: Iterable[RenderFinalSection] | None) -> str:
    """Render already-resolved final sections for the HTML preview."""

    return "".join(render_final_sections_html_by_id(final_sections).values())
