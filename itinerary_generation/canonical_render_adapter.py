"""Adapters from canonical content objects to the render contract.

Canonical objects remain useful while row logic is migrated, but the render model
itself should stay independent of any upstream builder/model layer.
"""

from __future__ import annotations

from itinerary_generation.canonical_model import CanonicalBlock, CanonicalDay
from itinerary_generation.render_model import RenderBlock, RenderDay, RenderMetaLine


def render_block_from_canonical(block: CanonicalBlock) -> RenderBlock:
    """Convert a canonical block to the UI-neutral render contract."""

    return RenderBlock(
        kind=block.kind,
        row_id=block.row_id,
        section_title=block.section_title,
        title=block.title,
        meta=[RenderMetaLine(meta.label, meta.value) for meta in block.meta],
        includes=list(block.includes),
        description=block.description,
        notable_sights=list(block.notable_sights),
        lines=list(block.lines),
        css_class=f"{block.kind}-block" if block.kind else "",
        source_row_ids=list(block.source_row_ids),
        warnings=list(block.warnings),
    )


def render_day_from_canonical(day: CanonicalDay) -> RenderDay:
    """Convert a canonical day shell and blocks to the render contract."""

    return RenderDay(
        day=day.day,
        number=day.number,
        city=day.city,
        title=day.title,
        intro=day.intro,
        blocks=[render_block_from_canonical(block) for block in day.blocks],
        source_row_ids=list(day.source_row_ids),
        warnings=list(day.warnings),
    )
