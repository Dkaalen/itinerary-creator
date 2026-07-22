"""Canonical Norway in a Nutshell signature-product naming."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from itinerary_generation.nutshell_domain import resolve_nutshell_journey


def canonical_nutshell_title(rows: Sequence[Mapping[str, object]], default: str = "Norway in a Nutshell") -> str:
    """Return the strongest source-backed client title for a Nutshell journey."""

    titles: list[str] = []
    for source_row in rows or ():
        journey = resolve_nutshell_journey(dict(source_row))
        if journey is None:
            continue
        title = str(journey.client_title or "").strip()
        if title and title not in titles:
            titles.append(title)
    if not titles:
        return default
    return max(titles, key=lambda title: (" to " in title.casefold(), len(title)))


__all__ = ["canonical_nutshell_title"]
