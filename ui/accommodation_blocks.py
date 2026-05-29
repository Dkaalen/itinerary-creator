"""Accommodation block HTML renderer."""

from itinerary_generation.canonical_builder import canonical_accommodation_block
from ui.render_helpers import esc


def render_accommodation_block(row):
    """Render a canonical accommodation block as the existing accommodation HTML shape."""

    block = canonical_accommodation_block(row)
    html_text = f'<div class="content-block accommodation-block" data-row-id="{esc(block.row_id)}">'
    html_text += f'<div class="section-title">{esc(block.section_title)}</div>'
    html_text += f'<div class="body-text strong-line">{esc(block.title)}</div>'
    for line in block.lines:
        html_text += f'<div class="body-text muted-note">{esc(line)}</div>'
    html_text += "</div>"
    return {"kind": block.kind, "row_id": block.row_id, "html": html_text}
