"""Fact extraction helpers for composed activity descriptions."""

from __future__ import annotations

import re
from typing import Iterable

from text_polish import polish_client_text

from itinerary_generation.description_patterns import LANDMARKS, RAW_OR_NON_PREMIUM_PATTERNS
from itinerary_generation.description_sources import _clean_inline


def _extract_landmarks(text: str, *, limit: int = 7) -> list[str]:
    found: list[str] = []
    for label, pattern in LANDMARKS:
        if re.search(pattern, text, flags=re.I) and label not in found:
            found.append(label)
        if len(found) >= limit:
            break
    return found


def _extract_inclusion_facts(row: dict, *, limit: int = 5) -> list[str]:
    facts: list[str] = []
    for raw in row.get("includes", []) or []:
        item = _clean_inline(raw).strip(" •-*|:.")
        if not item:
            continue
        lower = item.lower()
        if any(skip in lower for skip in ["pick-up", "drop-off", "transfer", "transport", "wifi", "wi-fi", "fees", "taxes", "ticket", "guide", "photography"]):
            continue
        item = re.sub(r"\bwith transfers?\b", "", item, flags=re.I).strip(" ,-:.")
        if item and item not in facts:
            facts.append(polish_client_text(item).strip(" ."))
        if len(facts) >= limit:
            break
    return facts


def _join(items: Iterable[str], *, max_items: int = 5) -> str:
    clean = [str(item).strip(" .") for item in items if str(item).strip(" .")]
    clean = clean[:max_items]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return ", ".join(clean[:-1]) + f" and {clean[-1]}"


def _focus_from_title(title: str) -> str:
    t = re.sub(r"^(Explore|Discover|Hike|Visit|Experience|Enjoy|Watch)\s+", "", title, flags=re.I).strip()
    lower = t.lower()
    if "borgarfjör" in lower or "borgarfjord" in lower:
        return "the Borgarfjörður region and its waterfalls"
    if "snæfellsnes" in lower or "snaefellsnes" in lower:
        return "the Snæfellsnes Peninsula"
    if "golden circle" in lower:
        return "the Golden Circle"
    if "south coast" in lower and "glacier" in lower:
        return "the South Coast waterfalls and glacier landscape"
    if "jökulsárlón" in lower or "jokulsarlon" in lower:
        return "Jökulsárlón Glacier Lagoon, Diamond Beach and the ice cave landscape"
    if "eastfjords" in lower:
        return "the Eastfjords and local life"
    if "north iceland" in lower:
        return "North Iceland"
    if "whale" in lower:
        return "Whale Watching"
    if "blue lagoon" in lower and "volcano" in lower:
        return "the Fagradalsfjall volcano area and the Blue Lagoon"
    return t[:1].lower() + t[1:] if t else "the day’s main experience"


def _has_bad_residue(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in RAW_OR_NON_PREMIUM_PATTERNS)


