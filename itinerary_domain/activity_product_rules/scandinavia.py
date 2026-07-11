"""Scandinavia city, ticket and museum activity matching."""

from __future__ import annotations

from typing import Any

from itinerary_domain.activity_product_core import ActivityProductFingerprint, match_product


def _ticket_title(source_title: str, fallback: str) -> str:
    if source_title and len(source_title) <= 80:
        lower = source_title.lower()
        if any(marker in lower for marker in ("ticket", "tickets", "admission", "entrance", "museum", "tivoli", "skyview", "munch", "vasa")):
            return source_title
    return fallback


def match_scandinavia_activity(
    row: dict[str, Any] | None,
    source: str,
    source_lower: str,
    source_title: str,
) -> ActivityProductFingerprint | None:
    """Match Helsinki, Copenhagen, Stockholm and generic Scandinavian products."""

    if "copenhagen" in source_lower and "city walking" in source_lower and "canal" in source_lower:
        return match_product("copenhagen_walking_canal", "walking_boat_tour", "Copenhagen Walking & Canal Tour", source_title=source_title)

    if "copenhagen" in source_lower and "canal" in source_lower and "walking" not in source_lower and any(marker in source_lower for marker in ("cruise", "boat", "harbor", "harbour")):
        return match_product("copenhagen_canal_cruise", "canal_cruise", source_title if source_title and "canal" in source_title.lower() else "Copenhagen Canal Cruise", source_title=source_title)

    if "tivoli" in source_lower:
        return match_product("tivoli_gardens_ticket", "ticket", _ticket_title(source_title, "Tivoli Gardens Entrance Ticket"), source_title=source_title)

    if "stockholm" in source_lower and "vasa" in source_lower and "old town" in source_lower:
        return match_product("stockholm_vasa_old_town_boat", "walking_museum_boat_tour", "Stockholm Must-See Tour with Vasa Museum, Old Town & Boat Trip", source_title=source_title)

    if "stockholm" in source_lower and "city highlights" in source_lower and "boat" in source_lower:
        return match_product("stockholm_city_highlights_boat", "boat_tour", "Stockholm City Highlights Boat Tour", source_title=source_title)

    if "stockholm" in source_lower and "vasa" in source_lower and any(marker in source_lower for marker in ("ticket", "tickets", "entrance", "entry", "admission", "museum")):
        return match_product("vasa_museum_ticket", "admission", _ticket_title(source_title, "Vasa Museum Entrance Ticket"), source_title=source_title)

    if "archipelago" in source_lower and "stockholm" in source_lower:
        return match_product("stockholm_archipelago_tour", "boat_tour", "Stockholm Archipelago Tour with Guide", source_title=source_title)

    if "skyview" in source_lower or "sky high views" in source_lower:
        return match_product("skyview_stockholm_ticket", "ticket", _ticket_title(source_title, "SkyView Stockholm Ticket"), source_title=source_title)

    if "sigtuna" in source_lower:
        return match_product("sigtuna_city_walk", "walking_tour", "Sigtuna City Walk", source_title=source_title)

    if "gothenburg" in source_lower and ("boat ride" in source_lower or "göta river" in source_lower or "goth-river" in source_lower):
        return match_product("gothenburg_gota_river_boat", "boat_tour", "Gothenburg Göta River Boat Ride", source_title=source_title)

    if "helsinki" in source_lower and "suomenlinna" in source_lower:
        return match_product("helsinki_suomenlinna_day_tour", "city_fortress_tour", "Helsinki City Highlights & Suomenlinna Day Tour", source_title=source_title)

    if "finntastic" in source_lower:
        return match_product("finntastic_helsinki_walk", "walking_tour", "A Finntastic Walking Tour in Helsinki", source_title=source_title)

    if "porvoo" in source_lower:
        return match_product("helsinki_porvoo_half_day", "guided_half_day_tour", "Porvoo Half-Day Sightseeing Tour", source_title=source_title)

    return None
