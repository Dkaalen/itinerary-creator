"""Compact experience-summary phrasing."""
from __future__ import annotations

from itinerary_generation.client_text_decisions import destination_logistics_phrase, is_destination_logistics_only
from itinerary_generation.destination_copy import destination_arc_fallback
from itinerary_generation.summaries_text import _compact_arc_phrase, _has

def _logistics_only_phrase(rows, signals):
    if signals.primary_experience_rows or not is_destination_logistics_only(rows):
        return ""
    text = signals.text
    if _has(text, "northern light village", "panorama suite"):
        return "Northern Lights village stay"
    if signals.has_nutshell:
        city = signals.chapter_city.casefold()
        if city in {"flåm", "flam"}:
            return "Scenic rail journey to Flåm"
        if city == "bergen" and _has(text, "fjord cruise", "gudvangen", "voss"):
            return "Fjord cruise and rail to Bergen"
        return "Norway in a Nutshell and scenic rail"
    if _has(text, "spend time at leisure onboard the cruise") and signals.row_types == {"Cruise"}:
        return "Coastal cruise at leisure"
    if _has(text, "cruise to bergen") and _has(text, "kirkenes"):
        return "Cruise departure towards Bergen"
    if _has(text, "cruise arrival to bergen", "arrival to bergen"):
        return "Cruise arrival and Bergen stay"
    if signals.has_leisure and signals.chapter_city:
        return destination_arc_fallback(signals.chapter_city)
    return destination_logistics_phrase(rows, chapter=signals.chapter_city)


def _compact_experience_phrase(candidates, chapter_city):
    primary = candidates[0]
    if len(candidates) > 1:
        combined = f"{primary}, {candidates[1].lower()}"
        if len(combined) <= 48 and not any(word in primary.lower() for word in candidates[1].lower().split()[:2]):
            return _compact_arc_phrase([combined, primary], chapter=chapter_city)
    return _compact_arc_phrase([primary], chapter=chapter_city)

