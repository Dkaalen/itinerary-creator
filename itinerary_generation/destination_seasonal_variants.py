"""Destination profile and seasonal-variant classification."""
from __future__ import annotations

from itinerary_generation.destination_registry import NordicDestination


def destination_copy_profile(record: NordicDestination | None) -> str:
    return record.copy_profile if record and record.copy_profile else "destination"
