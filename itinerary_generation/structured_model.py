"""Strongly typed itinerary document primitives.

This module is deliberately presentation-free: it has no Streamlit, HTML, PDF,
or image-bank dependencies.  It gives the app a stable source-of-truth shape
that can be migrated into preview, editor and PDF code over time without another
large rewrite.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

DocumentItemKind = Literal[
    "activity",
    "accommodation",
    "transfer",
    "flight",
    "rail",
    "ferry",
    "cruise",
    "rental_vehicle",
    "leisure",
    "arrival",
    "departure",
    "note",
    "unknown",
]

WarningSeverity = Literal["info", "warning", "error"]


@dataclass(slots=True, frozen=True)
class SourceRowRef:
    """Immutable pointer back to the normalized source row.

    Every client-facing object should carry one or more of these references so
    one supplier row cannot accidentally overwrite or absorb a different row.
    """

    row_id: str
    line_number: int | None
    day: str
    source_type: str
    effective_type: str
    start_date: str = ""
    end_date: str = ""
    city: str = ""
    raw_text: str = ""
    title: str = ""
    original_title: str = ""
    commercial_status: str = "included"
    commercial_reason: str = ""


@dataclass(slots=True, frozen=True)
class ModelWarning:
    code: str
    message: str
    severity: WarningSeverity = "warning"
    source_row_ids: tuple[str, ...] = ()


@dataclass(slots=True)
class DocumentItem:
    item_id: str
    kind: DocumentItemKind
    day: str
    date: str
    destination: str
    title: str
    source_row_ids: tuple[str, ...]
    commercial_status: str = "included"
    confidence: float = 1.0
    detail_lines: tuple[str, ...] = ()
    warnings: tuple[ModelWarning, ...] = ()


@dataclass(slots=True)
class DayDocument:
    day: str
    number: str
    date: str = ""
    destination: str = ""
    item_ids: tuple[str, ...] = ()
    source_row_ids: tuple[str, ...] = ()
    warnings: tuple[ModelWarning, ...] = ()


@dataclass(slots=True)
class StructuredListItem:
    label: str
    detail_lines: tuple[str, ...] = ()
    source_row_ids: tuple[str, ...] = ()
    category: str = ""


@dataclass(slots=True)
class StructuredListSection:
    section_id: str
    title: str
    items: tuple[StructuredListItem, ...] = ()


@dataclass(slots=True)
class ItineraryDocument:
    source_rows: tuple[SourceRowRef, ...] = ()
    days: tuple[DayDocument, ...] = ()
    items: tuple[DocumentItem, ...] = ()
    inclusions: tuple[StructuredListSection, ...] = ()
    exclusions: tuple[StructuredListSection, ...] = ()
    warnings: tuple[ModelWarning, ...] = ()

    def as_dict(self) -> dict:
        """Return a plain-JSON-compatible representation for debugging/tests."""

        return asdict(self)

    def items_by_kind(self, kind: DocumentItemKind) -> tuple[DocumentItem, ...]:
        return tuple(item for item in self.items if item.kind == kind)
