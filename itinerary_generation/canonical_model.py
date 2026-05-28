"""Canonical client-facing itinerary content objects.

The renderer should receive these objects rather than deciding from raw supplier
rows.  Raw row dictionaries may still be used by the canonical builder as source
material, but client-facing titles, descriptions, logistics and inclusions are
resolved here first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BlockKind = Literal[
    "activity",
    "accommodation",
    "travel_sequence",
    "self_transfer",
    "self_arranged_travel",
    "arrival",
    "departure",
    "leisure",
    "cruise_leisure",
    "day_overview",
    "included",
]


@dataclass(slots=True)
class CanonicalMetaLine:
    label: str
    value: str


@dataclass(slots=True)
class CanonicalBlock:
    kind: BlockKind
    row_id: str = ""
    section_title: str = ""
    title: str = ""
    meta: list[CanonicalMetaLine] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    description: str = ""
    notable_sights: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    html: str = ""  # temporary bridge for blocks not yet decomposed
    source_row_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CanonicalDay:
    day: str
    number: str
    city: str
    title: str
    intro: str
    blocks: list[CanonicalBlock] = field(default_factory=list)
    source_row_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
