"""Typed inclusion-contract helpers for regression tests.

Tests should exercise the production structured inclusion authority directly.
These helpers only provide concise text projections for assertions; they do not
recreate the retired dictionary-shaped production API.
"""

from __future__ import annotations

from collections.abc import Iterable

from itinerary_generation.structured_inclusions import build_structured_inclusion_sections
from itinerary_generation.structured_model import StructuredListItem, StructuredListSection


def build_inclusion_sections(
    parsed_rows: Iterable[dict],
    grouped_days: dict[str, list[dict]] | None = None,
) -> tuple[StructuredListSection, ...]:
    """Build inclusions through the production structured authority."""

    return build_structured_inclusion_sections(parsed_rows, grouped_days)


def inclusion_item_text(item: StructuredListItem) -> str:
    """Return the client-visible text represented by one typed item."""

    return "\n".join((item.label, *item.detail_lines))


def inclusion_item_texts(section: StructuredListSection) -> tuple[str, ...]:
    """Return client-visible item strings for one typed section."""

    return tuple(inclusion_item_text(item) for item in section.items)


def inclusion_section(
    sections: Iterable[StructuredListSection],
    title: str,
) -> StructuredListSection | None:
    """Return the typed section with the requested title, when present."""

    return next((section for section in sections if section.title == title), None)


def inclusion_section_text(
    sections: Iterable[StructuredListSection],
    title: str,
) -> str:
    """Return all client-visible item text for one section."""

    section = inclusion_section(sections, title)
    return "" if section is None else "\n".join(inclusion_item_texts(section))


def inclusion_text(
    sections: Iterable[StructuredListSection],
    *,
    include_titles: bool = False,
) -> str:
    """Return a flat client-visible text projection for assertions."""

    lines: list[str] = []
    for section in sections:
        if include_titles:
            lines.append(section.title)
        lines.extend(inclusion_item_texts(section))
    return "\n".join(lines)
