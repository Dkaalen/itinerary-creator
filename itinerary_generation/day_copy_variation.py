"""Controlled deterministic phrase variation for day-brain copy."""

from __future__ import annotations

import hashlib
from typing import Sequence

from itinerary_generation.day_facts import DayFacts, row_text
from itinerary_generation.day_intent import DayIntent


def copy_variation_key(facts: DayFacts, intent: DayIntent | str = "") -> int:
    """Return a stable integer key for non-random copy variation."""

    payload = "|".join([str(intent), *(row_text(row) for row in facts.rows)])
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def choose_copy_variant(options: Sequence[str], facts: DayFacts, intent: DayIntent | str = "") -> str:
    """Pick one approved option deterministically."""

    clean_options = tuple(option for option in options if str(option or "").strip())
    if not clean_options:
        return ""
    return clean_options[copy_variation_key(facts, intent) % len(clean_options)]


__all__ = ["choose_copy_variant", "copy_variation_key"]
