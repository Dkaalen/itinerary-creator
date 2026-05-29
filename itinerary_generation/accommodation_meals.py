"""Accommodation meal display helpers."""
from __future__ import annotations

import re


def meal_text_is_already_in_inclusions(includes, meal_text: str) -> bool:
    """Return true when a meal phrase is already present in inclusion text."""

    if not meal_text:
        return False

    source = " ".join(str(item or "") for item in (includes or []))
    normalized = re.sub(r"[^a-z0-9]+", " ", source.lower())
    normalized = f" {normalized} "
    meal = meal_text.lower()

    if "breakfast and dinner" in meal:
        return " breakfast " in normalized and " dinner " in normalized
    if "breakfast" in meal:
        return " breakfast " in normalized
    if "dinner" in meal:
        return " dinner " in normalized
    if "half board" in meal:
        return " half board " in normalized
    if "full board" in meal:
        return " full board " in normalized

    compact_meal = re.sub(r"[^a-z0-9]+", " ", meal).strip()
    return bool(compact_meal and f" {compact_meal} " in normalized)
