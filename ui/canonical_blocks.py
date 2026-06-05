"""Render canonical itinerary blocks to HTML.

This module is the first extraction step from ``ui.day_blocks``.  It keeps
canonical activity and accommodation HTML rendering separate from day-row
orchestration so ``ui.day_blocks`` can become a thinner coordinator over time.
"""

from itinerary_generation.canonical_builder import canonical_accommodation_block, canonical_activity_block
from itinerary_generation.render_model import RenderBlock, render_block_from_canonical
from ui.render_helpers import esc, render_list_items


def _render_activity_render_block(block: RenderBlock) -> dict:
    """Render an activity RenderBlock as the existing activity HTML shape."""

    html_text = f'<div class="content-block activity-block" data-row-id="{esc(block.row_id)}">'
    html_text += f'<div class="section-title">{esc(block.section_title)}</div>'
    html_text += f'<div class="body-text strong-line">{esc(block.title)}</div>'

    for meta in block.meta:
        if meta.value:
            html_text += f'<div class="body-text"><span class="meta-label">{esc(meta.label)}:</span> {esc(meta.value)}</div>'

    if block.includes:
        html_text += '<div class="section-title small-section">Included With This Experience</div>'
        html_text += render_list_items(block.includes)

    if block.description:
        html_text += '<div class="section-title small-section">Description</div>'
        html_text += f'<div class="body-text muted-note">{esc(block.description)}</div>'

    if block.notable_sights:
        html_text += '<div class="section-title small-section">Notable Sights</div>'
        html_text += render_list_items(block.notable_sights)

    html_text += "</div>"

    return {"kind": block.kind, "row_id": block.row_id, "html": html_text}


def render_accommodation_block(row):
    """Resolve a row through canonical content, then render the UI-neutral block."""

    return _render_accommodation_render_block(render_block_from_canonical(canonical_accommodation_block(row)))


def render_activity_block(row):
    """Resolve a row through canonical content, then render the UI-neutral block."""

    return _render_activity_render_block(render_block_from_canonical(canonical_activity_block(row)))


def _render_accommodation_render_block(block: RenderBlock) -> dict:
    """Render an accommodation RenderBlock as the existing accommodation HTML shape."""

    html_text = f'<div class="content-block accommodation-block" data-row-id="{esc(block.row_id)}">'
    html_text += f'<div class="section-title">{esc(block.section_title)}</div>'
    html_text += f'<div class="body-text strong-line">{esc(block.title)}</div>'
    for line in block.lines:
        html_text += f'<div class="body-text muted-note">{esc(line)}</div>'
    html_text += "</div>"
    return {"kind": block.kind, "row_id": block.row_id, "html": html_text}
