"""Extract explicit accommodation amenities from hotel supplier rows."""

from __future__ import annotations

import re

from normalizer_modules.text_utils import clean_space
from text_polish import polish_client_text


def extract_hotel_amenities(source: str) -> list[str]:
    """Return explicit included stay amenities from a hotel row.

    This is intentionally conservative.  It only promotes simple supplier
    markers that clearly describe access included with the stay, such as hotel
    sauna access, and avoids turning general hotel marketing prose into
    guaranteed inclusions.
    """

    text = clean_space(source)
    amenities: list[str] = []

    def add(value: str) -> None:
        cleaned = polish_client_text(value).strip(" .")
        if cleaned and cleaned.lower() not in {item.lower() for item in amenities}:
            amenities.append(cleaned)

    if re.search(r"\baccess\s+to\s+(?:the\s+)?hotel\s+sauna\b", text, flags=re.IGNORECASE):
        add("Access to the hotel sauna")

    return amenities


__all__ = ["extract_hotel_amenities"]
