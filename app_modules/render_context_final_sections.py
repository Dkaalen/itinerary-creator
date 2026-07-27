"""Final-section render contract helpers.

Preview and typed PDF export should resolve inclusions, exclusions, notes and
manual final pages once, then consume the same RenderFinalSection objects.
"""

from __future__ import annotations

from typing import Any

from itinerary_domain.field_sanitation import (
    CustomerField,
    normalize_customer_note_paragraphs,
    sanitize_customer_list,
)
from itinerary_generation.editor_page_contract import final_section_is_hidden as contract_final_section_is_hidden
from itinerary_generation.render_model import RenderFinalPage, RenderFinalSection, RenderSection
from itinerary_generation.structured_rendering import normalize_structured_list_sections
from ui.inclusion_pages import paginate_categorized_inclusions


def _structured_sections_to_render_sections(sections: Any) -> list[RenderSection]:
    render_sections: list[RenderSection] = []
    for section in normalize_structured_list_sections(sections):
        items: list[str] = []
        for item in section.items:
            lines = [item.label, *item.detail_lines]
            items.append("\n".join(line for line in lines if line))
        if items:
            render_sections.append(RenderSection(section.title, items))
    return render_sections


def _paginated_structured_final_pages(sections: Any) -> list[RenderFinalPage]:
    pages: list[RenderFinalPage] = []
    for page_sections in paginate_categorized_inclusions(sections):
        render_sections = _structured_sections_to_render_sections(page_sections)
        if render_sections:
            pages.append(RenderFinalPage(sections=render_sections))
    return pages


def _split_list_final_pages(
    items: list[str],
    field: CustomerField,
    *,
    items_per_page: int = 24,
) -> list[RenderFinalPage]:
    clean_items = sanitize_customer_list(items or [], field)
    return [RenderFinalPage(items=clean_items[index:index + items_per_page]) for index in range(0, len(clean_items), items_per_page)]


def _paragraph_final_pages(text: Any) -> list[RenderFinalPage]:
    paragraphs = normalize_customer_note_paragraphs(text)
    return [RenderFinalPage(paragraphs=paragraphs)] if paragraphs else []


def _html_final_pages(page_htmls: list[str] | str) -> list[RenderFinalPage]:
    values = page_htmls if isinstance(page_htmls, list) else [page_htmls]
    return [RenderFinalPage(content_html=str(value or "")) for value in values if str(value or "").strip()]


def _safe_label(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _final_section_is_hidden(context: Any, section_id: str) -> bool:
    return contract_final_section_is_hidden(context.hidden_page_ids, section_id)


def _final_section_title(context: Any, section_id: str, fallback: str) -> str:
    return _safe_label((context.final_section_titles or {}).get(section_id), fallback)


def build_final_sections_for_pdf(context: Any, *, include_hidden: bool = False) -> list[RenderFinalSection]:
    """Build final pages for the shared RenderDocument contract."""

    sections: list[RenderFinalSection] = []
    section_hidden = (lambda section_id: False) if include_hidden else (lambda section_id: _final_section_is_hidden(context, section_id))

    if not section_hidden("whats_included") and context.typed_inclusions_owned:
        if context.typed_inclusion_pages:
            sections.append(RenderFinalSection("whats_included", _final_section_title(context, "whats_included", "What’s included"), pages=_html_final_pages(context.typed_inclusion_pages), css_class="categorized-inclusions-page"))
    elif (
        not section_hidden("whats_included")
        and context.output_edits.get("whats_included_pages_html")
        and not getattr(context, "saved_inclusion_pages_refreshable", False)
    ):
        sections.append(RenderFinalSection("whats_included", _final_section_title(context, "whats_included", "What’s included"), pages=_html_final_pages(context.output_edits.get("whats_included_pages_html")), css_class="categorized-inclusions-page"))
    elif not section_hidden("whats_included") and context.output_edits.get("whats_included_html"):
        sections.append(RenderFinalSection("whats_included", _final_section_title(context, "whats_included", "What’s included"), pages=_html_final_pages(context.output_edits.get("whats_included_html")), css_class="categorized-inclusions-page"))
    elif not section_hidden("whats_included") and context.manual_whats_included:
        sections.append(RenderFinalSection("whats_included", _final_section_title(context, "whats_included", "What’s included"), pages=_split_list_final_pages(context.whats_included, CustomerField.INCLUSION)))
    elif not section_hidden("whats_included"):
        sections.append(RenderFinalSection("whats_included", _final_section_title(context, "whats_included", "What’s included"), pages=_paginated_structured_final_pages(context.categorized_inclusions), css_class="categorized-inclusions-page"))

    if context.optional_addons:
        optional_pages = []
        for index in range(0, len(context.optional_addons), 8):
            page_items = []
            for addon in context.optional_addons[index:index + 8]:
                if not isinstance(addon, dict):
                    continue
                heading_bits = [str(addon.get("title", "")).strip(), str(addon.get("date", "")).strip()]
                heading = " - ".join(bit for bit in heading_bits if bit)
                details = []
                if addon.get("time"):
                    details.append(f'Time: {addon["time"]}')
                if addon.get("duration"):
                    details.append(f'Duration: {addon["duration"]}')
                if addon.get("meeting_point"):
                    details.append(f'{addon.get("meeting_label") or "Meeting point"}: {addon["meeting_point"]}')
                if addon.get("description"):
                    details.append(str(addon.get("description", "")))
                elif addon.get("includes"):
                    details.append("Includes " + ", ".join(str(item) for item in addon.get("includes") or [] if str(item).strip()))
                else:
                    details.append("Available as an optional experience.")
                page_items.append("\n".join(sanitize_customer_list([heading, *[detail for detail in details if detail]], CustomerField.DESCRIPTION)))
            if page_items:
                optional_pages.append(RenderFinalPage(items=page_items))
        if optional_pages:
            sections.append(RenderFinalSection("optional_experiences", _final_section_title(context, "optional_experiences", "Optional Experiences"), pages=optional_pages, css_class="optional-addons-page"))

    if not section_hidden("whats_not_included") and context.typed_exclusions_owned:
        if context.typed_exclusion_html:
            sections.append(RenderFinalSection("whats_not_included", _final_section_title(context, "whats_not_included", "What’s not included"), pages=_html_final_pages(context.typed_exclusion_html), css_class="categorized-exclusions-page"))
    elif (
        not section_hidden("whats_not_included")
        and context.output_edits.get("whats_not_included_html")
        and not getattr(context, "saved_exclusion_html_refreshable", False)
    ):
        sections.append(RenderFinalSection("whats_not_included", _final_section_title(context, "whats_not_included", "What’s not included"), pages=_html_final_pages(context.output_edits.get("whats_not_included_html")), css_class="categorized-exclusions-page"))
    elif not section_hidden("whats_not_included") and context.output_edits.get("whats_not_included_text"):
        sections.append(RenderFinalSection("whats_not_included", _final_section_title(context, "whats_not_included", "What’s not included"), pages=_split_list_final_pages(context.whats_not_included, CustomerField.EXCLUSION)))
    elif not section_hidden("whats_not_included"):
        sections.append(RenderFinalSection("whats_not_included", _final_section_title(context, "whats_not_included", "What’s not included"), pages=_paginated_structured_final_pages(context.structured_whats_not_included), css_class="categorized-exclusions-page"))

    notes_pages = _paragraph_final_pages(context.important_travel_notes)
    if notes_pages and not section_hidden("important_travel_notes"):
        sections.append(RenderFinalSection("important_travel_notes", _final_section_title(context, "important_travel_notes", "Important travel notes"), pages=notes_pages, css_class="important-notes-page"))

    for page in context.manual_pages:
        html = str(page.get("content_html") or "").strip()
        if html:
            sections.append(RenderFinalSection(
                str(page.get("page_id") or "manual_page"),
                str(page.get("title") or "Custom page"),
                pages=_html_final_pages(html),
                css_class="manual-page",
            ))

    return [section for section in sections if section.pages or section.sections or section.items or section.paragraphs or section.content_html]
