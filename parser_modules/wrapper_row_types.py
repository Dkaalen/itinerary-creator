"""Resolve spreadsheet wrapper row types into their underlying itinerary type.

Some source workbooks use labels such as ``Extra Day`` to group optional route
extensions.  That label describes provenance, not the event itself.  The parser
keeps it in ``source_type`` while this module resolves the actual domain row
used by normalization and generation.
"""

from __future__ import annotations

import re

from parser_modules.common import normalize_type


def resolve_source_wrapper_type(item_type: object, description: object) -> str:
    normalized = normalize_type(item_type)
    if normalized != "Extra Day":
        return normalized

    text = " ".join(str(description or "").split()).casefold()
    if re.search(r"\bdeparture(?:\s+home|\s+flight|\s+transfer)?\b", text):
        return "Departure"
    if any(marker in text for marker in ("check in to your accommodation", "check-in to your accommodation", "night stay", "-star hotel", " hotel ")):
        return "Hotel"
    if any(marker in text for marker in ("flight to", "flight from", "domestic flight", "international flight")):
        return "Flight"
    if any(marker in text for marker in ("overnight train", "train to", "train from", "rail journey")):
        return "Train"
    if any(marker in text for marker in ("cruise to", "cruise from", "overnight cruise")):
        return "Cruise"
    if any(marker in text for marker in ("ferry to", "ferry from")):
        return "Ferry"
    if any(marker in text for marker in ("self transfer", "self-arranged transfer", "private transfer", "transfer to", "transfer from")):
        return "Transfer"
    if any(marker in text for marker in ("spend time at leisure", "day at leisure", "free time")):
        return "Leisure"
    if any(marker in text for marker in ("tour", "excursion", "ticket", "admission", "experience")):
        return "Activity"
    return normalized


__all__ = ["resolve_source_wrapper_type"]
