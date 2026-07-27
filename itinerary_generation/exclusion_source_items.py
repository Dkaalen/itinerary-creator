"""Extract source-row-specific exclusion labels."""

from __future__ import annotations

import re

from itinerary_domain.field_sanitation import CustomerField, sanitize_customer_field
from itinerary_generation.exclusion_row_rules import commercial_row_title
from text_polish import polish_client_text


def _split_exclusion_phrases(value: str) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\bfood\s+and\s+drinks\s+are\s+excluded\b", "Food and drinks", text, flags=re.IGNORECASE)
    parts: list[str] = []
    for line in text.splitlines():
        clean_line = line.strip(" •-*\t:.")
        if not clean_line:
            continue
        for part in re.split(r",\s*", clean_line):
            item = part.strip(" •-*\t:.")
            if item:
                parts.append(item)
    cleaned: list[str] = []
    for item in parts:
        lower = item.lower().strip(" .:")
        if not lower or lower in {"not included", "not included?", "excluded", "what's included", "what’s included"}:
            continue
        item = re.sub(r"^(?:not\s+included|excluded)\s*:?\s*", "", item, flags=re.IGNORECASE).strip(" .:")
        item = re.sub(r"\bdrop\s+to\s+hotel\b", "hotel drop-off", item, flags=re.IGNORECASE)
        item = re.sub(r"\btransportation\s+to\s+meeting\s+point\b", "transport to the meeting point", item, flags=re.IGNORECASE)
        item = re.sub(r"\bfood\s+and\s+drinks\s+are\s+excluded\b", "food and drinks", item, flags=re.IGNORECASE)
        item = sanitize_customer_field(polish_client_text(item), CustomerField.EXCLUSION).strip(" .:")
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _row_specific_not_included_items(row) -> list[str]:
    source = "\n".join(
        str(row.get(key, "") or "")
        for key in ["details", "original_title", "title"]
        if str(row.get(key, "") or "").strip()
    )
    direct_items: list[str] = []
    if re.search(r"\bwithout\s+meals?\b", source, flags=re.IGNORECASE):
        direct_items.append("Meals")

    if not re.search(r"\bnot\s+in(?:cl|lc)uded\b|\bexcluded\b|\bwithout\s+meals?\b|\bto\s+be\s+bought\s+on\s+(?:site|spot)\b|\btickets?\s+to\s+be\s+purchased\s+(?:locally|on\s+site)\b|\bticket\s+counter\b", source, flags=re.IGNORECASE):
        return []

    sections: list[str] = []
    for match in re.finditer(r"(?:^|\n)\s*not\s+in(?:cl|lc)uded\b\s*[:?]?", source, flags=re.IGNORECASE):
        after = source[match.end():]
        stop = re.search(
            r"(?:\n\s*)?(?:What\s+to\s+expect\??|What'?s\s+included\??|What’s\s+included\??|Overview|Highlights|Itinerary|Please\s+note|Important\s+info|Pick[-\s]*up\s*/\s*meeting\s*point)\b",
            after,
            flags=re.IGNORECASE,
        )
        if stop:
            after = after[:stop.start()]
        sections.append(after)

    for match in re.finditer(r"\b([^\n.;|]*?\b(?:are\s+)?excluded)\b", source, flags=re.IGNORECASE):
        sections.append(match.group(1))

    items: list[str] = list(direct_items)
    for section in sections:
        for item in _split_exclusion_phrases(section):
            if item and item not in items:
                items.append(item)
    return items


def _specific_cost_not_included_label(row) -> str:
    items = _row_specific_not_included_items(row)
    if not items:
        return ""
    title = sanitize_customer_field(commercial_row_title(row), CustomerField.TITLE)
    if not title:
        return ""
    phrase_items = []
    for index, item in enumerate(items):
        text = sanitize_customer_field(str(item or "").strip(), CustomerField.EXCLUSION)
        if index > 0 and text:
            text = text[:1].lower() + text[1:]
        phrase_items.append(text)
    if len(phrase_items) == 1:
        detail = phrase_items[0]
    else:
        detail = ", ".join(phrase_items[:-1]) + f" and {phrase_items[-1]}"
    return sanitize_customer_field(f"{title}: {detail}", CustomerField.EXCLUSION)
