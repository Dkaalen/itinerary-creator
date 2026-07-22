"""High-confidence and weak-evidence predicates for named products."""

from __future__ import annotations

import re

from itinerary_domain.product_rule_context import product_source_context_lower
from shared.url_metadata import strip_urls

_MUNCH_TITLE_RE = re.compile(r"\bmunch\s+museum\b", re.IGNORECASE)
_MUNCH_TICKET_RE = re.compile(
    r"(?:munch\s+museum[^.\n]{0,80}\b(?:ticket|tickets|admission|entry|entrance|visit)\b|"
    r"\b(?:ticket|tickets|admission|entry|entrance|visit)\b[^.\n]{0,80}munch\s+museum)",
    re.IGNORECASE,
)
_MUNCH_INCIDENTAL_RE = re.compile(
    r"(?:pass(?:ing)?|near|near to|close to|coastline|view of|stop at)\b[^.\n]{0,120}munch\s+museum",
    re.IGNORECASE,
)


def _title_evidence(row: dict | None, values: tuple[object, ...]) -> str:
    pieces: list[str] = []
    if row:
        pieces.extend(
            strip_urls(row.get(key, ""))
            for key in ("display_title", "title", "original_title")
            if row.get(key)
        )
    if not pieces and values:
        first = strip_urls(values[0])
        if first:
            pieces.append(re.split(r"\s*\|\s*|\s+-\s+(?:Time|Meeting point|Includes?|Description)\s*:", first, maxsplit=1, flags=re.IGNORECASE)[0])
    return " ".join(pieces)


def has_explicit_munch_museum_evidence(row: dict | None = None, *values: object) -> bool:
    """Require an explicit MUNCH Museum product, not a landmark mention.

    Cruise descriptions often mention passing MUNCH and stopping near museums.
    Those separate words must never be combined into a museum-ticket identity.
    """

    titleish = _title_evidence(row, values)
    if _MUNCH_TITLE_RE.search(titleish):
        return True

    source = product_source_context_lower(row, *values)
    if not _MUNCH_TITLE_RE.search(source):
        return False
    explicit = _MUNCH_TICKET_RE.search(source)
    incidental = _MUNCH_INCIDENTAL_RE.search(source)
    return bool(explicit and not incidental)


def has_explicit_fjellheisen_evidence(row: dict | None = None, *values: object) -> bool:
    lower = product_source_context_lower(row, *values)
    return "fjellheisen" in lower or (
        "trom" in lower
        and any(marker in lower for marker in ("cable car", "gondola", "mountain lift", "mountain cable", "aerial tramway"))
    )


def is_weak_tromso_viewpoint_ticket(row: dict | None = None, *values: object) -> bool:
    lower = product_source_context_lower(row, *values)
    return "round trip ticket" in lower and "trom" in lower and not has_explicit_fjellheisen_evidence(row, *values)
