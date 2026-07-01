"""Compatibility facade for split transport normalization helpers."""

from __future__ import annotations

from normalizer_modules.transport_activity_detection import (
    _is_rail_or_fjord_route_activity,
    _is_sightseeing_cruise_activity,
    is_rail_or_fjord_route_activity,
    is_sightseeing_cruise_activity,
)
from normalizer_modules.transport_rail_fjord import (
    _is_unbranded_rail_fjord_package,
    is_unbranded_rail_fjord_package,
)
from normalizer_modules.transport_title import normalize_transport_title
from normalizer_modules.transport_transfer_detection import (
    _is_route_transfer_activity,
    is_route_transfer_activity,
)

__all__ = [
    "normalize_transport_title",
    "is_unbranded_rail_fjord_package",
    "is_rail_or_fjord_route_activity",
    "is_sightseeing_cruise_activity",
    "is_route_transfer_activity",
    "_is_unbranded_rail_fjord_package",
    "_is_rail_or_fjord_route_activity",
    "_is_sightseeing_cruise_activity",
    "_is_route_transfer_activity",
]
