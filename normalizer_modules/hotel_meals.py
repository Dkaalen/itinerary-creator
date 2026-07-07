"""Hotel meal-plan and star-rating normalization."""

import re

from text_polish import polish_client_text


def normalize_meal_plan(value: str, source_text: str = "") -> str:
    text = f"{value} {source_text}".lower()
    if any(marker in text for marker in ("without breakfast", "without brekafast", "no breakfast", "breakfast not")): return "without breakfast"
    if "room only" in text: return "room only"
    if "self catering" in text or "self-catering" in text: return "self catering"
    if "half board" in text or "half-board" in text: return "half board"
    if "full board" in text or "full-board" in text: return "full board"
    if "breakfast" in text or "brekafast" in text or "breekfast" in text: return "breakfast and dinner" if "dinner" in text else "breakfast"
    if "dinner" in text: return "dinner"
    return polish_client_text(value)


def extract_star_level(value: str) -> str:
    match = re.search(r"\b([2-5](?:\s*/\s*[2-5])?)\s*[- ]?star\b", str(value or ""), flags=re.IGNORECASE)
    return re.sub(r"\s+", "", match.group(1)) if match else ""
