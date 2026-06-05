"""UI-neutral render objects for client-facing itinerary output.

The canonical layer resolves what the itinerary should say. Render objects are a
thin presentation contract consumed by HTML/PDF renderers, without importing UI
modules or storing generated HTML as the primary source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RenderMetaLine:
    label: str
    value: str


@dataclass(slots=True)
class RenderSection:
    title: str
    items: list[str] = field(default_factory=list)


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
    extra_sections: list[RenderSection] = field(default_factory=list)
    css_class: str = ""
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
