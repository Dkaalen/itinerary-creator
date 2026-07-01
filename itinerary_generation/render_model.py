"""UI-neutral render objects for client-facing itinerary output.

The canonical layer resolves what the itinerary should say. Render objects are a
thin presentation contract consumed by HTML/PDF renderers, without importing UI
modules or storing generated HTML as the primary source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RenderMetaLine:
    label: str
    value: str


@dataclass(slots=True)
class RenderSection:
    title: str
    items: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RenderCover:
    kicker: str = "Travel Itinerary"
    route_label: str = "Route"
    title: str = ""
    subtitle: str = ""
    dates: str = ""
    route: str = ""
    background_path: str = ""
    crop_focus: str = "top"
    ink: str = ""
    muted: str = ""
    accent: str = ""
    season: str = ""


@dataclass(slots=True)
class RenderSummary:
    trip_glance_title: str = "Your Trip at a Glance"
    trip_glance: list[RenderMetaLine] = field(default_factory=list)
    journey_arc_title: str = "Your Journey Arc"
    journey_arc_columns: dict[str, str] = field(default_factory=dict)
    journey_arc: list[dict[str, str]] = field(default_factory=list)
    background_path: str = ""
    crop_focus: str = "top"


@dataclass(slots=True)
class RenderFinalPage:
    sections: list[RenderSection] = field(default_factory=list)
    items: list[str] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    content_html: str = ""


@dataclass(slots=True)
class RenderFinalSection:
    section_id: str
    title: str
    pages: list[RenderFinalPage] = field(default_factory=list)
    sections: list[RenderSection] = field(default_factory=list)
    items: list[str] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    content_html: str = ""
    css_class: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RenderBlock:
    kind: str
    row_id: str = ""
    section_title: str = ""
    title: str = ""
    meta: list[RenderMetaLine] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    description: str = ""
    content_html: str = ""
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
    date: str = ""
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
    cover: RenderCover | None = None
    summary: RenderSummary | None = None
    final_sections: list[RenderFinalSection] = field(default_factory=list)
    hidden_page_ids: list[str] = field(default_factory=list)
    page_order: list[str] = field(default_factory=list)
