"""Activity block HTML renderer."""

from itinerary_generation.canonical_builder import canonical_activity_block
from ui.render_helpers import esc, render_list_items


def render_activity_block(row):
    """Render a canonical activity block as the existing activity HTML shape."""

    block = canonical_activity_block(row)

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
