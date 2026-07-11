"""Rail-and-fjord package detection for transport title normalization."""

from __future__ import annotations

from itinerary_domain.nutshell_parsing import is_source_backed_nutshell_route_package


def is_unbranded_rail_fjord_package(text: str) -> bool:
    """Return True for ticketed rail/fjord route packages without Nutshell ownership."""

    lower = str(text or "").lower()
    has_flam_train = any(
        marker in lower
        for marker in ("flåm train", "flam train", "flåm railway", "flam railway")
    )
    has_fjord_cruise = "nærøyfjord" in lower or "naeroyfjord" in lower or "fjord cruise" in lower
    has_ticketed_route = "e-tickets" in lower or "all tickets" in lower or "luggage transfer" in lower
    return (
        has_flam_train
        and has_fjord_cruise
        and has_ticketed_route
        and "norway in a nutshell" not in lower
        and not is_source_backed_nutshell_route_package(text)
    )


# Compatibility for older private imports.
_is_unbranded_rail_fjord_package = is_unbranded_rail_fjord_package


__all__ = ["is_unbranded_rail_fjord_package", "_is_unbranded_rail_fjord_package"]
