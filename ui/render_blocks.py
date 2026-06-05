"""HTML renderer for UI-neutral itinerary render blocks."""

from __future__ import annotations

from itinerary_generation.render_model import RenderBlock
from ui.render_helpers import esc, render_list_items


_KIND_CLASS = {
    "activity": "activity-block",
    "accommodation": "accommodation-block",
    "leisure": "leisure-block",
    "cruise_leisure": "cruise-leisure-block",
    "arrival": "arrival-block",
    "departure": "departure-block",
    "included": "included-block",
    "day_overview": "day-overview-block",
    "optional_experience": "optional-experience-block",
    "travel_sequence": "travel-sequence-block",
    "transport": "transport-block",
    "self_transfer": "self-transfer-block",
    "self_arranged_travel": "self-arranged-block",
}


def _block_classes(block: RenderBlock) -> str:
    classes = ["content-block"]
    if block.css_class:
        classes.extend(str(block.css_class).split())
    else:
        classes.append(_KIND_CLASS.get(block.kind, f"{block.kind}-block" if block.kind else "generic-block"))
    return " ".join(dict.fromkeys(cls for cls in classes if cls))


def _data_row_attr(block: RenderBlock) -> str:
    # Preserve the legacy HTML shape for synthetic aggregate blocks that did not
    # carry a source-row data attribute before the render contract migration.
    if block.kind in {"travel_sequence", "included"}:
        return ""
    return f' data-row-id="{esc(block.row_id)}"' if block.row_id else ""


def render_block_to_html(block: RenderBlock) -> dict:
    html_text = f'<div class="{esc(_block_classes(block))}"{_data_row_attr(block)}>'

    if block.section_title:
        html_text += f'<div class="section-title">{esc(block.section_title)}</div>'

    if block.title:
        html_text += f'<div class="body-text strong-line">{esc(block.title)}</div>'

    for meta in block.meta:
        if meta.value:
            html_text += f'<div class="body-text"><span class="meta-label">{esc(meta.label)}:</span> {esc(meta.value)}</div>'

    if block.kind == "activity":
        if block.includes:
            html_text += '<div class="section-title small-section">Included With This Experience</div>'
            html_text += render_list_items(block.includes)
        if block.description:
            html_text += '<div class="section-title small-section">Description</div>'
            html_text += f'<div class="body-text muted-note">{esc(block.description)}</div>'
        if block.notable_sights:
            html_text += '<div class="section-title small-section">Notable Sights</div>'
            html_text += render_list_items(block.notable_sights)
    elif block.kind == "transport":
        if block.includes:
            html_text += '<div class="section-title small-section">Includes</div>'
            html_text += render_list_items(block.includes)
        if block.description:
            html_text += f'<div class="body-text muted-note">{esc(block.description)}</div>'
    elif block.kind == "accommodation":
        for line in block.lines:
            html_text += f'<div class="body-text muted-note">{esc(line)}</div>'
    else:
        if block.lines:
            html_text += render_list_items(block.lines)
        if block.description:
            note_class = "muted-note" if block.kind in {"self_transfer", "self_arranged_travel", "optional_experience"} else ""
            class_attr = f' class="body-text {note_class}"' if note_class else ' class="body-text"'
            html_text += f'<div{class_attr}>{esc(block.description)}</div>'

    for section in block.extra_sections:
        if section.items:
            html_text += f'<div class="section-title small-section">{esc(section.title)}</div>'
            html_text += render_list_items(section.items)

    html_text += "</div>"
    return {"kind": block.kind, "row_id": block.row_id, "html": html_text}


def render_blocks_to_html(blocks: list[RenderBlock]) -> str:
    return "".join(render_block_to_html(block)["html"] for block in blocks if block)
