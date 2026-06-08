"""Tallinn day-excursion helpers shared by titles, day blocks and inclusions."""

from __future__ import annotations

import re

from text_polish import polish_inclusion_item, polish_title


_TALLINN_RE = re.compile(r"\btallin+n?\b", flags=re.IGNORECASE)
_CROSSING_MARKERS = (
    "departure from helsinki",
    "departure from tallinn",
    "return from tallinn",
    "helsinki port",
    "port transfer",
    "port transfers",
    "star class",
    "cruise ticket",
    "ferry ticket",
    "ferry tickets",
    "ferry crossing",
)


def tallinn_text(row: dict | None = None, *values: object) -> str:
    """Return lower-case text containing all Tallinn-relevant row context."""

    pieces: list[str] = []
    if row:
        for key in ["city", "title", "original_title", "details", "client_description"]:
            pieces.append(str(row.get(key, "") or ""))
        includes = row.get("includes", []) or []
        if isinstance(includes, (list, tuple, set)):
            pieces.extend(str(item or "") for item in includes)
        else:
            pieces.append(str(includes or ""))
    pieces.extend(str(value or "") for value in values)
    return " ".join(pieces).lower()


def mentions_tallinn(text: str) -> bool:
    return bool(_TALLINN_RE.search(str(text or "")))


def has_tallinn_crossing_markers(text: str) -> bool:
    lower = str(text or "").lower()
    return any(marker in lower for marker in _CROSSING_MARKERS)


def is_tallinn_ferry_framework(row: dict | None = None, *values: object) -> bool:
    """True for Helsinki↔Tallinn logistics rows, not the Old Town guide row."""

    text = tallinn_text(row, *values)
    if not mentions_tallinn(text):
        return False
    if "old town" in text and "guided" in text and not has_tallinn_crossing_markers(text):
        return False
    return has_tallinn_crossing_markers(text) or bool(re.search(r"\b(?:day\s+)?(?:excursion|day trip)\s+to\s+tallinn\b", text))


def is_tallinn_old_town_guided_tour(row: dict | None = None, *values: object) -> bool:
    """True only for the guided Old Town tour inside the Tallinn leisure time."""

    text = tallinn_text(row, *values)
    if not mentions_tallinn(text) or "old town" not in text:
        return False
    if not any(marker in text for marker in ["guided", "guide", "tour"]):
        return False
    return not has_tallinn_crossing_markers(text)


def tallinn_guidance_mode(row: dict | None = None, *values: object) -> str:
    """Return whether the Tallinn shore time is guided, self-guided or unclear.

    The ferry row can contain both logistics and Old Town wording. Self-guided
    language must win over the word "guided" because supplier rows often say
    "self guided tour".
    """

    text = tallinn_text(row, *values)
    if not mentions_tallinn(text):
        return "neutral"
    if re.search(r"\b(?:self[-\s]?guided|on\s+own|own\s+pace|free\s+time|leisure\s+time|explore\s+independently|explore\s+on\s+your\s+own)\b", text):
        return "self_guided"
    if re.search(r"\b(?:guided\s+(?:old\s+town\s+)?(?:walking\s+)?tour|old\s+town\s+guided|english[-\s]?speaking\s+guide|professional\s+guide)\b", text):
        return "guided"
    return "neutral"


def tallinn_ferry_description(row: dict | None = None) -> str:
    """Return client-safe ferry description without implying a guide."""

    mode = tallinn_guidance_mode(row)
    if mode == "self_guided":
        return (
            "Travel between Helsinki and Tallinn by ferry, with the crossings arranged so your time in Tallinn "
            "can focus on exploring the historic Old Town at your own pace."
        )
    if mode == "guided":
        return (
            "Travel between Helsinki and Tallinn by ferry, with time in Tallinn set aside for your guided Old Town experience."
        )
    return (
        "Travel between Helsinki and Tallinn by ferry, with the crossings arranged so your time in Tallinn "
        "can focus on the historic Old Town before returning to Helsinki."
    )


def tallinn_ferry_title(row: dict | None = None) -> str:
    text = tallinn_text(row)
    if "helsinki" in text:
        return "Helsinki to Tallinn return ferry" if ("departure from tallinn" in text or "return" in text) else "Helsinki to Tallinn ferry"
    return "Tallinn ferry journey"


def tallinn_departure_meta(row: dict | None = None) -> list[tuple[str, str]]:
    """Extract clean ferry timing meta lines from supplier text."""

    source = " ".join(str((row or {}).get(key, "") or "") for key in ["details", "original_title", "title"])
    meta: list[tuple[str, str]] = []
    for label, pattern in [
        ("Departure from Helsinki", r"departure\s+from\s+helsinki\s*:\s*([^\-|]+)"),
        ("Return from Tallinn", r"(?:departure|return)\s+from\s+tallinn\s*:\s*([^\-|]+)"),
    ]:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1).strip(" .,-:|")
        value = re.sub(r"\b(am|pm)\b", lambda m: m.group(1).upper(), value, flags=re.IGNORECASE)
        if value:
            meta.append((label, value))
    return meta


def clean_tallinn_ferry_inclusions(row: dict | None = None) -> list[str]:
    """Return ferry/logistics inclusions without moving guide wording onto ferry."""

    items = []
    row = row or {}
    raw_items = row.get("includes", []) or []
    if not isinstance(raw_items, (list, tuple, set)):
        raw_items = [raw_items]
    for raw_item in raw_items:
        item = str(raw_item or "").strip()
        lower = item.lower()
        if not item:
            continue
        # The guide/tour belongs to the detail row, not to the ferry framework.
        if any(marker in lower for marker in ["guided tour", "guide", "old town tour", "old town tallinn"]):
            continue
        if re.fullmatch(r"ferry tickets?", lower):
            cleaned = "Ferry tickets"
        elif re.fullmatch(r"cruise tickets?", lower):
            cleaned = "Cruise ticket"
        elif "star class" in lower and "ticket" in lower:
            cleaned = "Star Class cruise ticket"
        elif "port transfer" in lower:
            cleaned = "Helsinki port transfers"
        else:
            cleaned = polish_inclusion_item(item, tallinn_ferry_title(row)).strip(" .")
        if cleaned and cleaned not in items:
            items.append(cleaned)

    source = tallinn_text(row)
    fallback_candidates: list[str] = []
    if "port transfer" in source:
        fallback_candidates.append("Helsinki port transfers")
    if "star class" in source:
        fallback_candidates.append("Star Class cruise ticket")
    elif "cruise ticket" in source:
        fallback_candidates.append("Cruise ticket")
    elif "ferry ticket" in source:
        fallback_candidates.append("Ferry ticket")

    existing = " ".join(items).lower()
    for item in fallback_candidates:
        item_key = "ferry ticket" if "ferry ticket" in item.lower() else item.lower()
        if item_key not in existing:
            items.append(item)
            existing += " " + item.lower()

    return items
