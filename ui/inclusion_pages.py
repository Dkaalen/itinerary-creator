"""Categorized inclusion final page rendering."""

from __future__ import annotations

from ui.render_helpers import esc, render_list_items
from itinerary_generation.structured_rendering import normalize_structured_list_item, normalize_structured_list_sections


def _source_marker(item):
    structured_item = normalize_structured_list_item(item)
    if not structured_item or not structured_item.source_row_ids:
        return ""
    clean_ids = [str(row_id).strip() for row_id in structured_item.source_row_ids if str(row_id).strip()]
    if not clean_ids:
        return ""
    return f'<span class="source-row-marker" data-source-row-ids="{esc(",".join(clean_ids))}"></span>'


def _render_inclusion_item(item, *, bullet_multiline=False):
    structured_item = normalize_structured_list_item(item)
    if not structured_item or not structured_item.label:
        return ""

    source_marker = _source_marker(structured_item)
    lines = [structured_item.label, *structured_item.detail_lines]
    if len(lines) == 1:
        return f"<li>{esc(lines[0])}</li>{source_marker}"

    if bullet_multiline:
        detail_html = "".join(
            f'<div class="inclusion-entry-detail">{esc(line)}</div>'
            for line in lines[1:]
        )
        return (
            '<ul class="detail-list inclusion-category-list inclusion-multiline-list">'
            f'<li><div class="strong-line inclusion-entry-title">{esc(lines[0])}</div>{detail_html}</li>{source_marker}'
            '</ul>'
        )

    html_text = f'<div class="body-text strong-line inclusion-entry-title">{esc(lines[0])}</div>{source_marker}'
    for line in lines[1:]:
        html_text += f'<div class="body-text inclusion-entry-detail">{esc(line)}</div>'
    return html_text


def _render_plain_inclusion_items(items, *, as_entries: bool = False):
    normalized_items = [normalize_structured_list_item(item) for item in items]
    normalized_items = [item for item in normalized_items if item and item.label]
    if not normalized_items:
        return ""
    if as_entries:
        html_text = ""
        for index, item in enumerate(normalized_items):
            if index:
                html_text += '<div class="body-text inclusion-entry-spacer">&nbsp;</div>'
            html_text += f'<div class="body-text strong-line inclusion-entry-title">{esc(item.label)}</div>{_source_marker(item)}'
            for line in item.detail_lines:
                html_text += f'<div class="body-text inclusion-entry-detail">{esc(line)}</div>'
        return html_text
    if any(item.source_row_ids for item in normalized_items):
        list_items = "".join(_render_inclusion_item(item) for item in normalized_items)
        return f'<ul class="detail-list inclusion-category-list">{list_items}</ul>'
    return render_list_items([item.label for item in normalized_items], class_name="detail-list inclusion-category-list")


def render_inclusion_sections_inner_html(sections):
    clean_sections = normalize_structured_list_sections(sections)

    html_text = ""
    for section in clean_sections:
        html_text += '<div class="content-block inclusion-category-block">'
        html_text += f'<div class="section-title">{esc(section.title)}</div>'

        plain_items = []
        multiline_count = 0
        section_key = section.title.strip().lower()
        bullet_multiline = section_key not in {"accommodation", "activities & experiences"}
        plain_as_entries = section_key == "activities & experiences"
        for item in section.items:
            has_details = bool(item.detail_lines)
            if has_details:
                if plain_items:
                    html_text += _render_plain_inclusion_items(plain_items, as_entries=plain_as_entries)
                    plain_items = []
                if multiline_count and not bullet_multiline:
                    html_text += '<div class="body-text inclusion-entry-spacer">&nbsp;</div>'
                html_text += _render_inclusion_item(item, bullet_multiline=bullet_multiline)
                multiline_count += 1
            else:
                plain_items.append(item)

        if plain_items:
            html_text += _render_plain_inclusion_items(plain_items, as_entries=plain_as_entries)

        html_text += '</div>'
    return html_text


def _estimate_inclusion_item_units(item):
    structured_item = normalize_structured_list_item(item)
    if not structured_item:
        return 0
    lines = [structured_item.label, *structured_item.detail_lines]
    text = "\n".join(lines)
    # Detail lines render as separate block rows with their own line-height.
    # The previous 0.9 multiplier under-estimated dense hotel/activity entries,
    # allowing the browser/PDF renderer to split an explicit A4 page and leave
    # the next category orphaned on a mostly empty page.
    units = 1.5 + max(0, len(lines) - 1) * 1.2
    if len(text) > 110:
        units += 0.7
    if len(text) > 210:
        units += 0.7
    if len(text) > 330:
        units += 0.7
    return units


def _estimate_inclusion_section_units(section):
    """Approximate vertical space for keeping inclusion categories together.

    Categories are kept together whenever they can fit on the current page.
    If a category is too large for a single page, it is split without adding
    ugly "continued" wording to the client-facing page or section headings.
    """
    units = 3  # section title and spacing
    normalized = normalize_structured_list_sections([section])
    if not normalized:
        return 0
    for item in normalized[0].items:
        units += _estimate_inclusion_item_units(item)
    return units


def _split_oversized_inclusion_section(section, page_body_units):
    normalized = normalize_structured_list_sections([section])
    if not normalized:
        return []
    section_obj = normalized[0]
    section_title = section_obj.title
    chunks = []
    current_items = []
    current_units = 3

    for item in section_obj.items:
        item_units = _estimate_inclusion_item_units(item)
        if current_items and current_units + item_units > page_body_units:
            chunks.append({"title": section_title, "items": current_items})
            current_items = []
            current_units = 3
        current_items.append(item)
        current_units += item_units

    if current_items:
        chunks.append({"title": section_title, "items": current_items})

    return chunks or [section]


def paginate_categorized_inclusions(sections):
    """Return inclusion page sections using the PDF category-splitting rules."""

    clean_sections = [
        {"title": section.title, "items": list(section.items)}
        for section in normalize_structured_list_sections(sections)
    ]

    if not clean_sections:
        return []

    pages = []
    current = []
    current_units = 7  # final page title and top spacing
    max_units = 70
    empty_page_body_units = max_units - 7

    for section in clean_sections:
        candidate_sections = [section]
        if _estimate_inclusion_section_units(section) > empty_page_body_units:
            candidate_sections = _split_oversized_inclusion_section(section, empty_page_body_units)

        for candidate in candidate_sections:
            section_units = _estimate_inclusion_section_units(candidate)
            section_title = str(candidate.get("title") or "").strip().lower()
            keep_off_bottom = section_title == "private transfers" and current_units >= 55
            if current and (current_units + section_units > max_units or keep_off_bottom):
                pages.append(current)
                current = []
                current_units = 7
            current.append(candidate)
            current_units += section_units

    if current:
        pages.append(current)
    return pages


def render_inclusion_page_inner_htmls(sections):
    """Return one inner HTML fragment per categorized inclusion page."""

    return [render_inclusion_sections_inner_html(page_sections) for page_sections in paginate_categorized_inclusions(sections)]


def render_categorized_inclusions_pages(title, sections, page_class="final-list-page categorized-inclusions-page"):
    pages = paginate_categorized_inclusions(sections)
    if not pages:
        return ""

    html_text = ""
    for index, page_sections in enumerate(pages):
        inner_html = render_inclusion_sections_inner_html(page_sections)
        html_text += f'<div class="a4-page {esc(page_class)}"><div class="final-page-title">{esc(title)}</div>{inner_html}</div>'
    return html_text
