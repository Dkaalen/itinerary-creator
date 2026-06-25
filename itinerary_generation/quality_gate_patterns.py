"""Shared regex/message constants for itinerary quality gates."""

from __future__ import annotations

import re

FORBIDDEN_CLIENT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("forbidden_onward_flight", r"\bOnward\s+flight\b", "Use grounded destination or route wording."),
    ("forbidden_onward_travel", r"\bOnward\s+travel\b", "Use grounded destination or route wording."),
    ("weak_journey_arc_flight_connection", r"\bFlight\s+connection\b", "Use destination welcome wording when only a flight/check-in happens."),
    ("weak_journey_arc_travel_connection", r"\b(?:Scenic\s+)?Travel\s+connection\b", "Use the actual route or destination, not generic connection filler."),
    ("weak_onward_train", r"\bonward\s+train\b", "Describe the real experience or route, not 'onward train'."),
    ("weak_onward_connection", r"\bonward\s+connections?\b", "Describe the real destination or route instead of generic onward connections."),
    ("weak_travel_continues", r"\bTravel\s+continues\b", "Use destination welcome wording or a grounded route description."),
    ("supplier_parenthetical_unlimited", r"\(\s*unlimited\s*\)", "Remove supplier parenthetical '(unlimited)'."),
    ("supplier_parenthetical_if_snow", r"\(\s*if\s+snow\s*\)", "Remove supplier parenthetical '(if snow)'."),
    ("rough_airport_wording", r"\bto\s+Airport\b", "Use 'to the airport' or a named airport."),
)

AURORA_REVIEW_PATTERN = re.compile(r"\bAurora\b", flags=re.IGNORECASE)

PRICE_CLIENT_PATTERN_MESSAGE = "Supplier prices, costs and currency values must not appear in client-facing output."

SUPPLIER_TIME_WARNING_RE = re.compile(
    r"\b(?:before\s+departure|bring\s+warm\s+clothes|please\s+arrive|meeting\s+point|"
    r"voucher|subject\s+to|pick[-\s]?up\s+window|\d+\s*(?:min\.?|minutes?)\s+before)\b",
    flags=re.IGNORECASE,
)

SUSPICIOUS_AM_PM_TIME_RANGE_RE = re.compile(
    r"\b12:[0-5]\d\s*a\.?m\.?\s*[-–—]\s*(?:1[0-2]|0?[1-9]):[0-5]\d\s*p\.?m\.?\b",
    flags=re.IGNORECASE,
)

RAW_SUPPLIER_FIELD_RE = re.compile(
    r"\b(?:what[’']?s\s+included|what\s+to\s+expect|booking\s+information|"
    r"please\s+note|important\s+information|supplier\s+note|operator\s+note)\b",
    flags=re.IGNORECASE,
)
