"""Shared safety checks for client-facing itinerary titles.

Keep these checks renderer-agnostic so day titles, activity titles and small
content-block headings reject the same supplier/admin fragments before preview
or PDF export.
"""
from __future__ import annotations

import re


BAD_TITLE_PATTERNS: tuple[str, ...] = (
    r"\barrival\s+[^,|]+,\s*pick[-\s]?up\b",
    r"\bpick[-\s]?up\s+minibus\b",
    r"\bpick[-\s]?up\s*/\s*drop[-\s]?off\b",
    r"\bprivate\s+(?:airport|hotel|station)\s+to\b",
    r"\bshuttle\s*/?\s*flybus\b",
    r"\bwith\s+transfers?\b",
    r"\bcost\s+not\s+included\b",
    r"\bself[-\s]?arranged\b",
    r"\bwhat'?s\s+included\b",
    r"\boverview\b",
    r"\bopening hours\b",
    r"\bincludese\b",
    r"\bleisure as requested\b",
    r"\bself\s+transfer\s+to\b",
    r"\bfinal\s+timing\s+to\s+be\s+shared\s+in\s+voucher\b",
    r"\btrain\s+to\s+be\s+shared\s+in\s+voucher\b",
    r"\b(?:timing|time|details?)\s+to\s+be\s+shared\s+in\s+voucher\b",
    r"\b(?:voucher|admin)\s+wording\b",
    r"\bprice\s+is\s+per\s+(?:passenger|person|pax)\b",
    r"\bsingle\s+supplement\s+fee\b",
    r"\bcheck\s+availability\b",
)


CTA_PREFIX_PATTERN = re.compile(
    r"^\s*(?:book\s+today|book\s+now|check\s+availability)\s*[:\-–|]+\s*",
    flags=re.IGNORECASE,
)


def strip_supplier_title_cta(value: str) -> str:
    """Remove supplier call-to-action prefixes while preserving real titles."""
    return CTA_PREFIX_PATTERN.sub("", str(value or "")).strip()


def is_forbidden_client_title(value: str) -> bool:
    """Return True for raw supplier/admin fragments unsafe as visible titles."""
    text = str(value or "").strip()
    if not text:
        return False
    lower = text.lower()
    if re.fullmatch(r"book\s+today|book\s+now|check\s+availability", lower, flags=re.IGNORECASE):
        return True
    return any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in BAD_TITLE_PATTERNS)
