"""Public accessors for the Nordic destination registry."""

from __future__ import annotations

from itinerary_generation.data.nordic_destination_registry import (
    NordicDestination,
    destination_country_for_alias,
    destination_for_alias,
    is_southern_coastal_destination,
    registry_city_aliases,
    registry_records,
    travel_destination_records,
)

__all__ = [
    "NordicDestination",
    "destination_country_for_alias",
    "destination_for_alias",
    "is_southern_coastal_destination",
    "registry_city_aliases",
    "registry_records",
    "travel_destination_records",
]
