"""Canonical commercial-status text markers shared by parser and generation.

Keep this module dependency-free so parsing, row filtering, inclusions, and
future validation layers can agree on the same supplier wording policy.
"""

from __future__ import annotations

from typing import Any

SELF_ARRANGED_MARKERS: tuple[str, ...] = (
    "self arranged",
    "self arrnaged",
    "self arrnage",
    "self arrange",
    "own arrangement",
    "cost not included",
    "cost not inclueded",
    "price not included",
    "flight cost not",
    "ticket to be bought on spot",
    "ticket to be bought on site",
    "tickets to be bought on spot",
    "tickets to be bought on site",
    "ticket to be purchased locally",
    "tickets to be purchased locally",
    "ticket to be purchased on site",
    "tickets to be purchased on site",
    "to be paid locally",
    "ticket counter",
    "on spot",
    "on site",
)

SELF_ARRANGED_SQUASHED_MARKERS: tuple[str, ...] = tuple(
    marker.replace(" ", "") for marker in SELF_ARRANGED_MARKERS
)


def normalize_commercial_text(*values: Any) -> str:
    """Return compact lower-case text for commercial-status matching."""

    text = " ".join(str(value or "") for value in values).lower().replace("-", " ")
    return " ".join(text.replace(",", " ").split())


def has_self_arranged_marker(*values: Any) -> bool:
    """Return whether supplier text contains a self-arranged/excluded-cost marker."""

    compact = normalize_commercial_text(*values)
    squashed = compact.replace(" ", "")
    return any(marker in compact for marker in SELF_ARRANGED_MARKERS) or any(
        marker in squashed for marker in SELF_ARRANGED_SQUASHED_MARKERS
    )
