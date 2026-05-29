"""Inclusion item cleanup rules for itinerary output."""

from __future__ import annotations

import re

from text_polish import polish_inclusion_item, polish_inclusion_items
from itinerary_generation.content_text import clean_inline
from itinerary_generation.title_cleanup import has_raw_supplier_residue, repair_common_supplier_typos


def sanitize_inclusion_item(value: str, title: str = "") -> str:
    item = repair_common_supplier_typos(clean_inline(value)).strip(" •-*|:")
    if not item:
        return ""
    lower = item.lower()
    if lower in {"local", "included", "includes", "what's included", "what’s included", "overview", "description"}:
        return ""
    if any(marker in lower for marker in ["not included", "price", "supplement", "checkout", "book your", "check availability"]):
        return ""
    if has_raw_supplier_residue(item) and len(item.split()) > 10:
        return ""
    item = re.sub(r"^Local,\s*English-speaking guide$", "Local English-speaking guide", item, flags=re.I)
    item = re.sub(r"^English-speaking guide$", "English-speaking guide", item, flags=re.I)
    item = re.sub(r"Thermal clothing \(overalls$", "Thermal clothing (overalls, shoes, wool socks and gloves)", item, flags=re.I)
    return polish_inclusion_item(item, title)


def merge_compound_inclusions(items: list[str]) -> list[str]:
    merged: list[str] = []
    for raw in items:
        item = sanitize_inclusion_item(raw)
        if not item:
            continue
        lower = item.lower().strip(" .")
        if lower == "english-speaking guide" and merged and merged[-1].lower().strip(" .") in {"local", "experienced"}:
            prefix = merged[-1].strip(" .")
            merged[-1] = f"{prefix} English-speaking guide"
            continue
        if lower == "personal experience" and merged and merged[-1].lower().strip(" .") == "live host for a fun":
            merged[-1] = "Live host for a fun, personal experience"
            continue
        if lower in {"shoes", "gloves", "wool socks", "shoes, wool socks, gloves)"} and merged and "thermal clothing" in merged[-1].lower():
            if item.lower() not in merged[-1].lower():
                merged[-1] = merged[-1].rstrip(" .)") + f", {item})"
            continue
        if item not in merged:
            merged.append(item)
    return polish_inclusion_items(merged)
