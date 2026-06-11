"""Iceland-specific activity product matching."""

from __future__ import annotations

from typing import Any

from itinerary_generation.activity_product_core import ActivityProductFingerprint, match_product


def match_iceland_activity(
    row: dict[str, Any] | None,
    source: str,
    source_lower: str,
    source_title: str,
) -> ActivityProductFingerprint | None:
    """Match Iceland activity families."""

    if "blue lagoon" in source_lower:
        if "volcano" in source_lower or "fagradalsfjall" in source_lower or "eruption" in source_lower:
            return match_product("blue_lagoon_volcano", "guided_day_tour", "Blue Lagoon & Volcano Eruption Site Tour", source_title=source_title)
        return match_product("blue_lagoon_admission", "admission", "Blue Lagoon Admission", source_title=source_title)

    if "sky lagoon" in source_lower:
        return match_product("sky_lagoon_saman_pass", "admission", "Sky Lagoon Saman Pass & 7-Step Ritual", source_title=source_title)

    if "silfra" in source_lower and ("snork" in source_lower or "drysuit" in source_lower):
        return match_product("silfra_drysuit_snorkelling", "snorkelling", "Drysuit Snorkelling in Silfra", source_title=source_title)

    if "whale" in source_lower and ("watching" in source_lower or "marine" in source_lower or "safari" in source_lower):
        if "arctic wildlife" in source_lower or "rib boat" in source_lower or "wildlife safari" in source_lower:
            title = "Whale Watching & Arctic Wildlife Safari by RIB Boat" if "rib boat" in source_lower else "Whale Watching & Arctic Wildlife Safari"
            return match_product("arctic_whale_wildlife_safari", "whale_safari", title, source_title=source_title)
        if "tromsø" in source_lower or "tromso" in source_lower or "arctic cruise" in source_lower:
            return match_product("tromso_whale_safari", "whale_safari", "Winter Whale Safari by Arctic Cruise", source_title=source_title)
        if "marine" in source_lower:
            return match_product("reykjavik_whale_marine", "marine_cruise", "Whale & Marine Tour", source_title=source_title)
        if "from downtown" in source_lower:
            return match_product("reykjavik_whale_watching_downtown", "marine_cruise", "Whale Watching From Downtown", source_title=source_title)
        return match_product("whale_watching", "marine_cruise", "Whale Watching", source_title=source_title)

    if "golden circle" in source_lower:
        return match_product("golden_circle", "guided_day_tour", source_title if source_title and "golden circle" in source_title.lower() else "Golden Circle Tour", source_title=source_title)

    if "south coast" in source_lower and ("glacier" in source_lower or "black sand" in source_lower):
        title = "South Coast & Glacier Hike Minibus Expedition" if "glacier hike" in source_lower or "hike on" in source_lower else "South Coast, Glacier & Black Sand Beach Tour"
        return match_product("iceland_south_coast", "guided_day_tour", title, source_title=source_title)

    if "snæfellsnes" in source_lower or "snaefellsnes" in source_lower:
        return match_product("snaefellsnes_peninsula", "guided_day_tour", "Snæfellsnes Peninsula Tour", source_title=source_title)

    return None
