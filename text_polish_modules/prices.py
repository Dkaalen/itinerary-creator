"""Price-fragment cleanup for client-facing optional add-on text."""

from __future__ import annotations

import re

from text_polish_modules.text_cleanup import clean_space


_PRICE_FRAGMENT_PATTERNS = [
    r"\b(?:optional\s+add[- ]?on\s*)?at\s*(?:from\s*)?(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)\s*\d[\d.,]*(?:\s*/\s*(?:person|pax|passenger|adult|child))?",
    r"\b(?:optional\s+add[- ]?on\s*)?at\s*(?:from\s*)?\d[\d.,]*\s*(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)(?:\s*/\s*(?:person|pax|passenger|adult|child))?",
    r"\b(?:price|cost|supplement|single traveler supplement fee)\s*(?:is|from|at|:)?\s*(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)?\s*\d[\d.,]*(?:\s*(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£))?(?:\s*(?:per|/ )\s*(?:person|pax|passenger|adult|child))?",
    r"\b\d[\d.,]*\s*(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)\s*(?:per|/)?\s*(?:person|pax|passenger|adult|child)?",
    r"\b(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)\s*\d[\d.,]*\s*(?:per|/)?\s*(?:person|pax|passenger|adult|child)?",
    r"\bprice\s+is\s+per\s+(?:passenger|person|pax)\b",
]


def strip_price_fragments(value: str) -> str:
    """Remove prices from optional add-ons without removing the experience itself."""
    text = str(value or "")
    if not text:
        return ""
    for pattern in _PRICE_FRAGMENT_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bOptional\s+Add[- ]?on\b\s*[:|,-]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bOptinal\s+Add[- ]?on\b\s*[:|,-]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\|\s*\|\s*", " | ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return clean_space(text).strip(" -:|,.;")


