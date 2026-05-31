"""Train-specific client-facing detail helpers."""
from __future__ import annotations

import re

from text_polish import polish_title


def _normalize_cabin_quantity(value: str) -> str:
    text = polish_title(value).strip(" .,-:|")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^(\d+)\s*[xX]\s+", r"\1 x ", text)
    return text[:1].upper() + text[1:] if text else text


def _train_source_candidates(row: dict) -> list[str]:
    """Return train source fields separately, longest-noisy fallback last.

    Joining title/details/original_title before extracting cabins can create a
    false continuation, for example ``for two people Overnight Train: ...``.
    Cabin matching should therefore run per field and only fall back to joined
    text for very simple presence checks.
    """

    candidates = []
    for key in ("title", "details", "original_title"):
        value = str(row.get(key) or "").strip()
        if value and value not in candidates:
            candidates.append(value)
    joined = " ".join(candidates).strip()
    if joined and joined not in candidates:
        candidates.append(joined)
    return candidates


def _extract_train_cabin_from_text(source: str) -> str:
    source = str(source or "")
    if not source.strip():
        return ""

    stop = r"(?=\s*(?:$|[.,;|]|\s+-\s+|\s+Overnight\s+Train\b|\s+Train\s*[:|-]|\s+Transfer\b))"
    quantity_cabin_match = re.search(
        r"\b(\d+\s*x\s*(?:(?:upper|lower|downstairs|upstairs|inside|outside|private|standard|double|single|twin|family|sleeper|sleeping)\s+){0,5}(?:cabin|compartment)(?:s)?(?:\s+for\s+[^,;|.-]+?)?)" + stop,
        source,
        flags=re.IGNORECASE,
    )
    if quantity_cabin_match:
        return _normalize_cabin_quantity(quantity_cabin_match.group(1))

    cabin_match = re.search(r"\bcabin\s*\(([^)]+)\)", source, flags=re.IGNORECASE)
    if cabin_match:
        return f"{polish_title(cabin_match.group(1)).title()} sleeper cabin"

    descriptive_cabin_match = re.search(
        r"\b((?:(?:upper|lower|downstairs|upstairs|inside|outside|private|standard|double|single|twin|family|sleeper|sleeping)\s+){1,5}(?:cabin|compartment)(?:\s+for\s+[^,;|.-]+?)?)" + stop,
        source,
        flags=re.IGNORECASE,
    )
    if descriptive_cabin_match and re.search(r"\bovernight|night\s+train|santa\s+claus\s+express|sleeper|sleeping", source, flags=re.IGNORECASE):
        return _normalize_cabin_quantity(descriptive_cabin_match.group(1))

    return ""


def get_train_cabin_detail(row: dict) -> str:
    """Return supported sleeper-cabin detail for train rows only.

    The app should mention sleeper cabins when the input supports it, but should
    not invent a cabin for ordinary train journeys.
    """

    row_type = str(row.get("effective_type") or row.get("type") or "").strip().lower()
    if row_type != "train":
        return ""

    for source in _train_source_candidates(row):
        detail = _extract_train_cabin_from_text(source)
        if detail:
            return detail

    source = " ".join(_train_source_candidates(row))
    if re.search(r"\bsleeper\s+(?:cabin|compartment)\b|\bsleeping\s+(?:cabin|compartment)\b", source, flags=re.IGNORECASE):
        return "Sleeper cabin"

    if re.search(r"\bnight\s+train\b", source, flags=re.IGNORECASE) and re.search(r"\b(?:cabin|compartment)\b", source, flags=re.IGNORECASE):
        return "Sleeper cabin"

    return ""
