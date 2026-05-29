"""Client-facing formatting for self-drive and suggested-route rows."""
from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title

ACRONYMS = {"ATV", "SUV", "SPA"}
SPECIAL_PLACES = {
    "REYKJAVIK": "Reykjavík",
    "REYKJAVÍK": "Reykjavík",
    "KEFLAVIK": "Keflavík",
    "KEFLAVÍK": "Keflavík",
    "VIK": "Vík",
    "VÍK": "Vík",
    "KERID": "Kerið",
    "KERIÐ": "Kerið",
    "SILFRA": "Silfra",
    "GOLDEN CIRCLE": "Golden Circle",
    "SOUTH COAST": "South Coast",
    "DIAMOND BEACH": "Diamond Beach",
}

ADMIN_ROUTE_PATTERNS = [
    r"route\s+suggested",
    r"final timing",
    r"shared in voucher",
    r"voucher",
]


def _clean_piece(piece: str) -> str:
    text = polish_client_text(piece).strip(" •-*|:")
    if not text:
        return ""
    for pattern in ADMIN_ROUTE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.I).strip(" •-*|:")
    if not text:
        return ""
    # Remove leading city label while preserving the route itself.
    if ":" in text:
        left, right = [part.strip() for part in text.split(":", 1)]
        if len(left.split()) <= 3 and not re.search(r"\b(?:route|drive|waterfalls|glacier|lagoon)\b", left, flags=re.I):
            text = right.strip()
    upper = text.upper().strip()
    if upper in SPECIAL_PLACES:
        return SPECIAL_PLACES[upper]
    if upper in ACRONYMS:
        return upper
    text = re.sub(r"\bROute\b", "Route", text, flags=re.I)
    text = re.sub(r"\bSouth coast\b", "South Coast", text, flags=re.I)
    text = re.sub(r"\bGolden circle\b", "Golden Circle", text, flags=re.I)
    text = re.sub(r"\breturn drive\b", "return drive", text, flags=re.I)
    return polish_title(canonicalize_place_name(text) or text)


def format_suggested_route_items(text: str) -> tuple[str, list[str], list[str]]:
    """Return (section_title, route_items, optional_items)."""
    source = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lower = source.lower()
    section = "Suggested route"
    if "return drive" in lower or "scenic return" in lower:
        section = "Today’s route"
    if re.search(r"(^|[\n|])\s*explore\b", source, flags=re.I):
        section = "Explore at your own pace"

    source = re.sub(r"route\s+suggested\s*\|?", "", source, flags=re.I)
    source = source.replace("✅", "")
    items: list[str] = []
    optional: list[str] = []
    in_optional = False

    chunks = []
    if "\n" in source:
        for line in source.splitlines():
            chunks.extend(re.split(r"\s*\|\s*", line))
    else:
        chunks = re.split(r"\s*\|\s*", source)

    for raw in chunks:
        line = raw.strip(" •-*|:")
        if not line:
            continue
        if re.match(r"optional\s*:?", line, flags=re.I):
            in_optional = True
            line = re.sub(r"^optional\s*: ?", "", line, flags=re.I).strip()
            if not line:
                continue
        parts = [part for part in re.split(r"\s*\+\s*", line) if part.strip()]
        for part in parts:
            item = _clean_piece(part)
            if not item or item.lower() in {"route", "suggested", "included", "includes"}:
                continue
            target = optional if in_optional else items
            if item not in target:
                target.append(item)

    # If a route consists of short stop names, combine as a route line.
    if section == "Suggested route" and len(items) >= 3 and all(len(item.split()) <= 4 for item in items):
        return section, [" → ".join(items)], optional
    return section, items, optional
