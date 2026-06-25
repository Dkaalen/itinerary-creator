"""Public compatibility facade for destination profile services."""

from itinerary_generation.destination_profile_builder import (
    destination_identity, destination_profile_for, destination_profiles, is_known_destination,
)
from itinerary_generation.destination_profile_copy import (
    destination_arrival_intro, destination_leisure_sentence, destination_stay_intro,
    select_arrival_sentence, stable_variant_index,
)
from itinerary_generation.destination_profile_model import DestinationProfile

__all__ = [
    "DestinationProfile", "destination_arrival_intro", "destination_identity",
    "destination_leisure_sentence", "destination_profile_for", "destination_profiles",
    "destination_stay_intro", "is_known_destination", "select_arrival_sentence", "stable_variant_index",
]
