"""UI-neutral render objects for client-facing itinerary output.

The canonical layer resolves what the itinerary should say. Render objects are a
thin presentation contract consumed by HTML/PDF renderers, without importing UI
modules or storing generated HTML as the primary source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from itinerary_generation.canonical_model import CanonicalBlock, CanonicalDay


@dataclass(slots=True)
class RenderMetaLine:
    label: str
    value: str


@dataclass(slots=True)
class RenderBlock:
    kind: str
    row_id: str = ""
    section_title: str = ""
    title: str = ""
    meta: list[RenderMetaLine] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    description: str = ""
    notable_sights: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    source_row_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RenderDay:
    day: str
    number: str
    city: str
    title: str
    intro: str
    blocks: list[RenderBlock] = field(default_factory=list)
    source_row_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RenderDocument:
    title: str = ""
    subtitle: str = ""
    route: str = ""
    days: list[RenderDay] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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
