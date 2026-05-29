"""Shared constants and option normalization for itinerary generation."""

from __future__ import annotations


TRANSPORT_TYPES = ["Transport", "Train", "Flight", "Cruise", "Ferry"]

DETAIL_LEVELS = [
    "Elegant concise",
    "Standard client itinerary",
    "Rich descriptive",
]


def normalize_detail_level(value):
    value = str(value or "").strip()
    if value in DETAIL_LEVELS:
        return value
    return "Standard client itinerary"
