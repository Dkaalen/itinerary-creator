"""Train-specific client-facing detail helpers."""
from __future__ import annotations

import re

from text_polish import polish_title


_SLEEPER_CABIN_PATTERNS = [
    r"\bsleeper\s+cabin\b",
    r"\bsleeping\s+cabin\b",
    r"\bcabin\s*\(([^)]+)\)",
    r"\bnight\s+train\b.*\bcabin\b",
]


def get_train_cabin_detail(row: dict) -> str:
    """Return supported sleeper-cabin detail for train rows only.

    The app should mention sleeper cabins when the input supports it, but should
    not invent a cabin for ordinary train journeys.
    """

    row_type = str(row.get("effective_type") or row.get("type") or "").strip().lower()
    if row_type != "train":
        return ""

    source = " ".join(str(row.get(key) or "") for key in ("title", "details", "original_title"))
    if not source.strip():
        return ""

    cabin_match = re.search(r"\bcabin\s*\(([^)]+)\)", source, flags=re.IGNORECASE)
    if cabin_match:
        return f"{polish_title(cabin_match.group(1)).title()} sleeper cabin"

    if re.search(r"\bsleeper\s+cabin\b|\bsleeping\s+cabin\b", source, flags=re.IGNORECASE):
        return "Sleeper cabin"

    if re.search(r"\bnight\s+train\b", source, flags=re.IGNORECASE) and re.search(r"\bcabin\b", source, flags=re.IGNORECASE):
        return "Sleeper cabin"

    return ""
