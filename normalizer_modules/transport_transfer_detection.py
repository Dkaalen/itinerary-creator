"""Activity-row detection for pasted route transfers."""

from __future__ import annotations

import re

from normalizer_modules.text_utils import text_blob
from normalizer_modules.transport_activity_detection import is_sightseeing_cruise_activity


def is_route_transfer_activity(row: dict) -> bool:
    """Return True when an Activity row is really point-to-point transport."""

    text = text_blob(row).lower()
    if is_sightseeing_cruise_activity(text):
        return False
    if any(
        marker in text
        for marker in ["blue lagoon", "comfort ticket", "admission", "entry ticket", "return transfer"]
    ):
        if any(
            marker in text
            for marker in ["what's included", "overview", "what to expect", "ticket", "admission", "experience"]
        ):
            return False

    if re.search(r"\b(?:train|flight|coach|bus|ferry)\s*[:|]", text):
        return True
    if re.search(r"\bcruise\s*(?!time\b)[:|]", text):
        return True
    if re.search(
        r"\b(?:long[-\s]*distance|panorama|panoramic)\b[^.]{0,80}\b(?:coach|bus)\b[^.]{0,80}\btransfer\b[^.]{0,120}\bfrom\b[^.]{1,120}\bto\b",
        text,
    ):
        return True
    if (
        re.search(r"\b(?:coach|bus)\s+transfer\b[^.]{0,120}\bfrom\b[^.]{1,120}\bto\b", text)
        and "private" not in text
    ):
        return True
    return False


# Compatibility for older private imports.
_is_route_transfer_activity = is_route_transfer_activity


__all__ = ["is_route_transfer_activity", "_is_route_transfer_activity"]
