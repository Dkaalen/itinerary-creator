"""High-confidence fallback title matchers for activity rows.

The product registry and activity fingerprinting own known catalogue matches.  This
module only owns the remaining keyword-based fallbacks that used to live inside
``create_client_activity_title``.
"""

from __future__ import annotations

import re

from text_polish import polish_title


def _mentions_hop_on(full_text: str, title_text: str) -> bool:
    return (
        "hop-on" in title_text
        or "hop off" in title_text
        or "hop-off" in title_text
        or "hop on hop off" in full_text
    )


def match_keyword_activity_title(
    row: dict,
    *,
    title: str,
    original_title: str,
    details: str,
) -> str:
    """Return a client-facing keyword fallback title, or ``""``.

    These rules are intentionally ordered from specific to general.  They are
    not a replacement for the product registry; they protect legacy and messy
    supplier rows that do not yet have a registry entry.
    """

    title = str(title or "")
    title_text = title.lower()
    original_title_text = str(original_title or "").lower()
    full_text = f"{title_text} {original_title_text} {details}".lower()

    if "mostraumen" in full_text:
        return "Mostraumen Fjord Cruise"

    if "best view" in full_text and any(marker in full_text for marker in ["oslofjord", "oslo fjord", "nordmarka"]):
        return "Nordmarka Forest & Oslofjord View Hike"

    if "norwegian food tour" in full_text or ("food tour" in full_text and "oslo" in full_text):
        return "Oslo Food Tour"

    # Supplier rows often mention cafes/restaurants in local tips or exclusions;
    # that must not turn a Bergen history/city walk into a food tour.
    if ("walking tour" in title_text or "guided walking tour" in full_text) and not re.search(
        r"\b(food tour|tasting stops?|culinary tour|secret food)\b",
        full_text,
    ):
        return polish_title(title or original_title or "Guided Walking Tour")

    if "food" in full_text and "culture" in full_text and "bergen" in full_text:
        food_is_excluded = (
            re.search(r"\b(food|drinks?)\s+(?:and\s+drinks?\s+)?(?:are\s+)?excluded\b", full_text)
            or "food and drinks are excluded" in full_text
        )
        food_is_explicit_product = re.search(r"\b(food tour|tasting stops?|food walk|culinary|secret food)\b", full_text)
        if food_is_explicit_product and not food_is_excluded:
            return "Bergen Food & Culture Walk"

    if _mentions_hop_on(full_text, title_text):
        city = str(row.get("city", "") or "").strip()
        if "copenhagen" in full_text:
            return "Copenhagen Hop-On Hop-Off Bus Ticket"
        if "bergen" in full_text:
            return "Bergen Hop-On Hop-Off Bus Ticket"
        return f"Flexible {polish_title(city)} Sightseeing Ticket" if city else "Flexible City Sightseeing Ticket"

    if "blue lagoon" in full_text or "bluelagoon" in full_text:
        if any(marker in title_text for marker in ["volcano", "eruption", "fagradalsfjall"]):
            return polish_title(title)
        return "Blue Lagoon Admission"

    if "sky lagoon" in full_text or "skylagoon" in full_text:
        if "saman" in full_text or "7-step" in full_text or "7 step" in full_text:
            return "Sky Lagoon Saman Pass & 7-Step Ritual"
        return "Sky Lagoon Admission"

    if "silfra" in full_text and ("snork" in full_text or "drysuit" in full_text):
        return "Drysuit Snorkelling in Silfra"

    if "whale watching" in full_text:
        if any(marker in full_text for marker in ["arctic wildlife", "rib boat", "wildlife safari"]):
            return "Whale Watching & Arctic Wildlife Safari by RIB Boat" if "rib boat" in full_text else "Whale Watching & Arctic Wildlife Safari"
        if "from downtown" in full_text:
            return "Whale Watching From Downtown"
        return "Whale Watching"

    if "optional addon" in full_text and any(marker in full_text for marker in ["svolvær", "svolvaer", "svolaver", "svoalvaer"]):
        return "Optional experience in Svolvær"

    if "lofoten" in full_text and "trollfjord" in full_text:
        return "Lofoten Day Tour & Trollfjord Cruise"

    if "crystal lavvo" in full_text or ("lyngen" in full_text and "lavvo" in full_text):
        return "Lyngen Alps Crystal Lavvo Stay"

    if any(marker in title_text for marker in ["fløibanen", "floibanen"]) or any(
        marker in original_title_text for marker in ["fløibanen", "floibanen"]
    ):
        return "Fløibanen Funicular"

    if "arctic route" in full_text or ("senja" in full_text and "coach" in full_text):
        if not any(marker in full_text for marker in ["crystal lavvo", "overnight stay", "private crystal", "snowshoe", "basecamp"]):
            return "Arctic Route Coach Transfer"

    if "city walking" in full_text and "canal" in full_text and "copenhagen" in full_text:
        return "Copenhagen Walking & Canal Tour"

    if "svalbard bryggeri" in full_text or ("brewery" in full_text and "svalbard" in full_text):
        return "Svalbard Brewery Visit"

    if "longyearbyen in a nutshell" in full_text:
        return "Longyearbyen Guided Tour"

    if "wildlife photography" in full_text and "longyearbyen" in full_text:
        return "Wildlife Photography Around Longyearbyen"
    if "wildlife and glacier" in full_text:
        return "Wildlife & Glacier Experience"
    if "mountain hike" in full_text and "abisko" in full_text:
        return "Mountain Hike in Abisko"
    if title_text.startswith("round trip ticket"):
        return "Round Trip Ticket"

    return ""
