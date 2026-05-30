from __future__ import annotations

import re

from itinerary_generation.common import clean_client_title
from itinerary_generation.content_engine import (
    clean_client_title as engine_clean_client_title,
    cleaned_generic_activity_title,
)
from itinerary_generation.title_routes import (
    _extract_supplier_day_heading,
    _looks_like_norway_in_a_nutshell,
    _route_label_from_activity_text,
)
from itinerary_generation.title_safety import BAD_TITLE_PATTERNS, is_forbidden_client_title
from text_polish import polish_title, strip_price_fragments

def is_bad_raw_day_title(title: str) -> bool:
    text = str(title or "").strip()
    if not text:
        return True
    lower = text.lower()
    if len(text) > 85:
        return True
    return is_forbidden_client_title(text) or any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in BAD_TITLE_PATTERNS)



def normalize_client_day_title(title: str, row: dict | None = None) -> str:
    """Polish recurring supplier/admin titles into client-facing day titles.

    All day-title and inclusion-title paths should pass through this function so
    raw supplier/admin wording cannot re-enter the PDF from a different layer.
    """
    row = row or {}
    text = cleaned_generic_activity_title(title or "", row)
    full = f"{text} {row.get('title', '')} {row.get('original_title', '')} {row.get('details', '')}".lower()

    if _looks_like_norway_in_a_nutshell(full):
        route_label = _route_label_from_activity_text(full)
        # Day titles read better with the destination focus; inclusions can keep
        # the full from/to route wording.
        dest_match = re.search(r"\bto\s+([A-Za-zÀ-ÿøØåÅäÄöÖ]+)\s*$", route_label)
        if dest_match:
            return f"Norway in a Nutshell to {polish_title(dest_match.group(1))}"
        return route_label

    if not text or is_forbidden_client_title(text):
        city = polish_title(row.get("city", ""))
        return f"Experience in {city}" if city else "Experience"
    return polish_title(re.sub(r"\bToday\b\s*$", "", text, flags=re.IGNORECASE).strip(" -:|"))

def create_client_activity_title(row):
    title = clean_client_title(strip_price_fragments(row.get("title", "")))
    original_title = clean_client_title(strip_price_fragments(row.get("original_title", "") or title))
    details = str(row.get("details", "") or "")

    # First pass through the central title sanitizer. If it can identify a
    # high-confidence client-facing title (museum, leisure, raw ticket/admin
    # title, etc.), use it before older product-specific fallbacks.
    sanitized_title = engine_clean_client_title(title or original_title or details, row)
    if sanitized_title and not is_bad_raw_day_title(sanitized_title):
        title = sanitized_title

    supplier_heading = _extract_supplier_day_heading(row.get("original_title") or details)
    if supplier_heading and (title.lower().startswith("guided experience") or is_bad_raw_day_title(title)):
        title = supplier_heading

    if not title:
        for segment in re.split(r"\s*\|\s*|\s+-\s+", details):
            candidate = clean_client_title(strip_price_fragments(segment))
            if candidate and not candidate.lower().startswith(("optional addon", "optional add-on", "optional add on")):
                title = candidate
                break

    if is_bad_raw_day_title(title):
        title = ""

    title_text = str(title or original_title or "").lower()
    original_title_text = str(original_title or "").lower()
    full_text = f"{title_text} {original_title_text} {details}".lower()

    title = re.sub(r"\s+(?:with|incl\.?|including)\s+transfers?\b", "", str(title or ""), flags=re.IGNORECASE).strip(" -:|")
    title = re.sub(r"^Watch\s+Whales\b", "Whale Watching", title, flags=re.IGNORECASE).strip()
    title_text = title.lower()
    full_text = f"{title_text} {original_title_text} {details}".lower()

    if "munch" in full_text and "museum" in full_text:
        return "Munch Museum Visit"

    if "mostraumen" in full_text:
        return "Mostraumen Fjord Cruise"

    if "best view" in full_text and ("oslofjord" in full_text or "oslo fjord" in full_text or "nordmarka" in full_text):
        return "Nordmarka Forest & Oslofjord View Hike"

    if "norwegian food tour" in full_text or ("food tour" in full_text and "oslo" in full_text):
        return "Oslo Food Tour"

    if "food" in full_text and "culture" in full_text and "bergen" in full_text:
        return "Bergen Food & Culture Walk"

    if "hop-on" in title_text or "hop off" in title_text or "hop-off" in title_text or "hop on hop off" in full_text:
        city = str(row.get("city", "") or "").strip()
        return f"Flexible {polish_title(city)} Sightseeing Ticket" if city else "Flexible City Sightseeing Ticket"

    if _looks_like_norway_in_a_nutshell(f"{original_title} {title} {details}"):
        return _route_label_from_activity_text(f"{original_title} {title} {details}")

    if "santa claus" in full_text and "friends" in full_text:
        return "Meet Santa Claus and his friends"

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
        if "arctic wildlife" in full_text or "rib boat" in full_text or "wildlife safari" in full_text:
            return "Whale Watching & Arctic Wildlife Safari"
        if "from downtown" in full_text:
            return "Whale Watching From Downtown"
        return "Whale Watching"

    if "tallinn" in full_text:
        return "Day Trip to Tallinn"

    if "optional addon" in full_text and any(marker in full_text for marker in ["svolvær", "svolvaer", "svolaver", "svoalvaer"]):
        return "Optional experience in Svolvær"

    if "lofoten" in full_text and "trollfjord" in full_text:
        return "Lofoten Day Tour & Trollfjord Cruise"

    if "fløibanen" in full_text or "floibanen" in full_text:
        return "Fløibanen Funicular"

    if "arctic route" in full_text or "senja" in full_text and "coach" in full_text:
        return "Arctic Route Coach Transfer"

    if "hop-on" in title_text or "hop off" in title_text or "hop-off" in title_text or "hop on hop off" in full_text:
        if "copenhagen" in full_text:
            return "Copenhagen Hop-On Hop-Off Bus Ticket"
        if "bergen" in full_text:
            return "Bergen Hop-On Hop-Off Bus Ticket"
        return "Hop-On Hop-Off Bus Ticket"

    if "city walking" in full_text and "canal" in full_text and "copenhagen" in full_text:
        return "Copenhagen Walking & Canal Tour"

    if "wildlife photography" in full_text and "longyearbyen" in full_text:
        return "Wildlife Photography Around Longyearbyen"
    if "wildlife and glacier" in full_text:
        return "Wildlife & Glacier Experience"
    if "mountain hike" in full_text and "abisko" in full_text:
        return "Mountain Hike in Abisko"
    if "round trip ticket" in full_text and "trom" in full_text:
        return "Fjellheisen Cable Car"

    if title_text.startswith("round trip ticket"):
        return "Round Trip Ticket"

    title_has_northern_lights = (
        "northern light" in title_text
        or "aurora" in title_text
        or "borealis" in title_text
    )
    full_has_northern_lights = (
        "northern light" in full_text
        or "aurora" in full_text
        or "borealis" in full_text
    )
    title_has_northern_lights_activity_word = any(
        word in title_text
        for word in ["hunt", "chase", "basecamp", "base camp", "cruise", "boat", "float", "floating", "mileage"]
    )

    # Do not rename ordinary daytime/culture activities just because the long
    # supplier description mentions a chance of seeing northern lights.
    is_northern_lights = title_has_northern_lights or (
        full_has_northern_lights
        and (
            title_has_northern_lights_activity_word
            or any(word in full_text for word in ["northern lights cruise", "aurora cruise", "aurora basecamp", "ice floating"])
        )
    )

    if not is_northern_lights:
        return normalize_client_day_title(title, row)

    if "reindeer" in full_text and ("hunt" in full_text or "hunting" in full_text or "chase" in full_text):
        return "Northern Lights Hunt by Reindeer"

    if "basecamp" in full_text or "base camp" in full_text:
        return "Northern Lights Basecamp"

    if "cruise" in full_text or "boat" in full_text or "sailing" in full_text:
        return "Northern Lights Cruise"

    if "floating" in full_text or "float" in full_text:
        return "Northern Lights Ice Floating"

    if "chase" in full_text:
        return "Northern Lights Chase"

    if "hunt" in full_text or "mileage" in full_text or "photo tour" in full_text:
        return "Northern Lights Hunt"

    return "Northern Lights Experience"

