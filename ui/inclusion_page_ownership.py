"""Detect refreshable generated inclusion-page HTML fragments."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from bs4 import BeautifulSoup

from itinerary_generation.generated_ownership import html_text


def _coerce_html_pages(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        pages: list[str] = []
        for item in value:
            if isinstance(item, dict):
                pages.append(str(item.get("content_html") or item.get("html") or ""))
            else:
                pages.append(str(item or ""))
        return [page for page in pages if page.strip()]
    if isinstance(value, dict):
        page = str(value.get("content_html") or value.get("html") or "")
        return [page] if page.strip() else []
    page = str(value or "")
    return [page] if page.strip() else []


def _combined_text_signature(pages: Iterable[str]) -> str:
    return html_text("\n".join(str(page or "") for page in pages)).casefold()


def _source_marker_signature(pages: Iterable[str]) -> tuple[str, ...]:
    markers: list[str] = []
    for page in pages:
        soup = BeautifulSoup(str(page or ""), "html.parser")
        for marker in soup.select("[data-source-row-ids]"):
            value = str(marker.get("data-source-row-ids") or "").strip()
            if value:
                markers.append(value)
    return tuple(markers)


def inclusion_pages_match_generated(saved_pages: Any, generated_pages: Any) -> bool:
    """Return True when saved pages are generated content that can refresh.

    Older editor commits persisted auto-generated inclusion HTML as if it were
    manual content. The text/source signatures let layout and wording fixes
    refresh those pages while still preserving genuinely different user edits.
    """

    saved = _coerce_html_pages(saved_pages)
    generated = _coerce_html_pages(generated_pages)
    if not saved or not generated:
        return False

    if _combined_text_signature(saved) == _combined_text_signature(generated):
        return True

    saved_sources = _source_marker_signature(saved)
    generated_sources = _source_marker_signature(generated)
    return bool(saved_sources and saved_sources == generated_sources)


__all__ = ["inclusion_pages_match_generated"]
