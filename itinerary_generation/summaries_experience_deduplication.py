"""Stable first-occurrence duplicate control for experience candidates."""
from __future__ import annotations


def deduplicate_candidates(candidates):
    result = []
    seen = set()
    for candidate in candidates:
        key = str(candidate).casefold().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result
