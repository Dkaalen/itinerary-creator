"""Activity inclusion cleanup and fallback helpers for itinerary rendering.

These helpers are shared by day-page rendering, canonical activity building,
and final inclusion/optional-add-on pages. Keeping them outside final page
assembly avoids coupling core activity cleanup to final-page layout code.
"""

import re

from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.titles import create_client_activity_title
from text_polish import polish_inclusion_item, polish_inclusion_items, strip_price_fragments
from itinerary_generation.client_sanitizer import sanitize_client_text
from itinerary_generation.content_engine import merge_compound_inclusions, sanitize_inclusion_item
from itinerary_generation.render_text_helpers import normalize_list


def get_fallback_activity_inclusions(row):
    """Create sensible client-facing inclusions when supplier text has no formal inclusion list."""

    if row.get("suppress_fallback_inclusions") or row.get("group_tour_optional_extra"):
        return []

    title = create_client_activity_title(row) or row.get("title", "")
    source_items = normalize_list(row.get("includes", []))
    full_text = " ".join(
        [str(title), str(row.get("original_title", "")), str(row.get("details", ""))]
        + [str(item) for item in source_items]
    ).lower()

    if "blue lagoon" in full_text or "sky lagoon" in full_text or "lagoon admission" in full_text:
        inclusions = []
        if "access" in full_text or "admission" in full_text or "entry" in full_text or "ticket" in full_text:
            clean_title = re.sub(r"\b(admission|entrance|entry)\b", "", title.replace(" & 7-Step Ritual", ""), flags=re.IGNORECASE).strip(" -:|,")
            inclusions.append(f"{clean_title} admission" if clean_title else "Lagoon admission")
        if "7-step" in full_text or "7 step" in full_text or "ritual" in full_text:
            inclusions.append("Complete 7-step ritual")
        if "towel" in full_text:
            inclusions.append("Use of towel")
        if "bathrobe" in full_text:
            inclusions.append("Use of bathrobe")
        if "locker" in full_text:
            inclusions.append("Private locker")
        if "mask" in full_text:
            inclusions.append("Lagoon mask experience")
        if "drink" in full_text:
            inclusions.append("One drink of choice")
        return inclusions or ["Admission included"]

    if "tallin" in full_text or "tallinn" in full_text or title == "Day Trip to Tallinn":
        inclusions = []
        is_self_guided = bool(re.search(r"\bself[-\s]?guided\b", full_text, flags=re.IGNORECASE))
        if "port transfer" in full_text or "helsinki port" in full_text or "hotel pick" in full_text:
            inclusions.append("Helsinki port transfers")
        if "star class" in full_text:
            inclusions.append("Star Class ferry ticket")
        elif "ferry ticket" in full_text or "cruise ticket" in full_text or "day trip to tallinn" in str(title).lower():
            inclusions.append("Helsinki–Tallinn ferry crossing")
        if "old town" in full_text or "tallinn" in full_text or "tallin" in full_text:
            if is_self_guided:
                inclusions.append("Self-guided Old Town visit")
            elif "guided" in full_text:
                inclusions.append("Guided Old Town tour")
        if not inclusions:
            inclusions = ["Helsinki–Tallinn ferry crossing", "Time to explore Tallinn Old Town"]
        return inclusions

    if "essential oslo" in full_text or ("oslo" in full_text and "walking tour" in full_text):
        return ["Guided walking tour"]

    if "must-see bergen" in full_text or ("bergen" in full_text and "foot and boat" in full_text):
        return ["Guided walking tour", "Boat tour"]

    if "hop-on hop-off" in title.lower() or "hop-off" in title.lower() or "hop off" in title.lower() or "hop on hop off" in full_text:
        return ["24-hour Hop-On Hop-Off bus ticket"]

    if "fløibanen" in full_text or "floibanen" in full_text:
        if "round" in full_text or "roundtrip" in full_text or "round trip" in full_text:
            return ["Round-trip Fløibanen ticket"]
        return ["Fløibanen ticket"]

    if "icebreaker" in full_text and "cruise" in full_text:
        city = str(row.get("city", "") or "").strip()
        return [
            f"Shuttle bus from {city}" if city else "Shuttle bus transfer",
            "Icebreaker cruise",
            "Floating in icy Arctic waters in survival suits",
            "Walk on the frozen sea",
            "Complimentary hot drink",
            "Cruise & Swim certificate",
        ]

    if "walking" in full_text and "canal" in full_text:
        return ["Guided walking tour", "Canal experience"]

    if "whale watching" in full_text:
        if row.get("group_tour_optional_extra"):
            return []
        return ["Whale watching cruise", "Professional, English-speaking guide"]

    if "walking tour" in full_text or "guided" in full_text:
        return ["Guided experience"]

    if "ticket" in full_text or "admission" in full_text or "entry" in full_text:
        if "round-trip" in full_text or "round trip" in full_text or "return" in full_text:
            return ["Round-trip tickets"]
        return ["Tickets/admission included"]

    return []


def prioritize_inline_inclusions(items, max_items=6):
    """Keep inline inclusions clear and compact.

    Day pages should show the most useful inclusions without turning into an
    appendix. Prefer logistics, guide, transport, tickets/entrance, meals and
    special equipment; drop low-value accounting items when space is limited.
    """

    clean_items = []
    for item in polish_inclusion_items(normalize_list(items)):
        if not item or item in clean_items:
            continue
        lower = item.lower()
        if lower in {"guided experience", "experience as described in the day-by-day itinerary"} and len(items) > 1:
            continue
        if any(marker in lower for marker in ["tax", "service fee", "goods and services"]):
            continue
        if lower.startswith("duration") or " with panoramic views" in lower:
            continue
        if lower.startswith(("depart for ", "return to ", "departure from ", "return from ")):
            continue
        if "small group" in lower or ("max " in lower and "guest" in lower):
            continue
        # The title already tells the client they are visiting Santa Claus Village;
        # keep limited day-page inclusion space for more concrete inclusions like
        # snowmobiling, reindeer sleigh rides, winter equipment and lunch.
        if "fun visit to santa claus village" in lower:
            continue
        clean_items.append(item)

    def score(item):
        lower = item.lower()
        if "small group" in lower or ("max " in lower and "guest" in lower):
            return 99
        if "meteorological" in lower or "observation" in lower:
            return 98
        if "pick" in lower or "drop" in lower or "transfer" in lower:
            return 0
        if "reindeer" in lower or "snowmobile" in lower or "santa claus" in lower or "husky" in lower:
            return 1
        if any(marker in lower for marker in ["thermal", "overall", "winter clothes", "winter equipment", "equipment", "boots", "gloves", "balaclava", "helmet", "survival suit", "floating suit", "frozen sea"]):
            return 2
        if "meal" in lower or "lunch" in lower or "dinner" in lower or "drink" in lower or "snack" in lower or "cookies" in lower or "barbecue" in lower or "bbq" in lower or "berry juice" in lower:
            return 3
        if "hike" in lower or "canyon" in lower or "waterfall" in lower or "museum" in lower or "arktikum" in lower:
            return 4
        if "photo" in lower or "camera" in lower or "dslr" in lower:
            return 5
        if "ticket" in lower or "entrance" in lower or "ferry" in lower or "certificate" in lower:
            return 6
        if "guide" in lower or "guided" in lower or "certified" in lower:
            return 7
        if "transport" in lower or "coach" in lower or "minivan" in lower or "bus" in lower:
            return 8
        return 10

    ordered = sorted(enumerate(clean_items), key=lambda pair: (score(pair[1]), pair[0]))
    selected = [item for _, item in ordered[:max_items]]
    # Restore original order among selected items so the client-facing flow feels natural.
    return [item for item in clean_items if item in selected]


def looks_like_descriptive_prose(text):
    lower = str(text or "").lower()
    prose_markers = [
        "tour gives",
        "take a stroll",
        "listen to",
        "make sense",
        "to top it all",
        "waterworld",
        "best way to understand",
        "explore bergen from",
        "historic city streets",
    ]
    return len(str(text or "")) > 95 and any(marker in lower for marker in prose_markers)



def _polish_activity_bullet_case(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    replacements = {
        r"\bfull day transportation\b": "Full day transportation",
        r"\bguide and entrance tickets\b": "Guide and entrance tickets",
        r"\bfrederiksborg palace\b": "Frederiksborg Palace",
        r"\broskilde cathedral\b": "Roskilde Cathedral",
        r"\bthe viking ship museum\b": "The Viking Ship Museum",
        r"\bviking ship museum\b": "Viking Ship Museum",
        r"\bskip the line entrance\b": "Skip-the-line entrance",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def clean_activity_inclusion_items(items, title=""):
    clean_items = []
    for item in normalize_list(items):
        text = polish_inclusion_item(sanitize_client_text(strip_price_fragments(str(item).strip())), title)
        lower = text.lower().strip(":? ")

        text = re.split(r"\s+-\s+(?:Description|Overview)\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:")
        lower = text.lower().strip(":? ")

        if lower in {"what's included", "what’s included", "includes", "included", "description", "overview"}:
            continue
        if re.search(r"^not\s+in(?:cl|lc)uded\b|^excluded\b", lower, flags=re.IGNORECASE):
            continue
        if re.search(r"\b(price|cost|supplement)\b", lower, flags=re.IGNORECASE) and re.search(r"\b(per person|per passenger|eur|nok|usd|gbp|dkk|sek|isk|kr|€|\$|£|\d)\b", lower, flags=re.IGNORECASE):
            continue
        if "included excluded" in lower or "food and drinks are excluded" in lower:
            continue

        # Avoid long overview prose on the inclusion page.
        if looks_like_descriptive_prose(text):
            continue
        if len(text) > 150 and "included" not in lower:
            continue
        if "icebreaker" in str(title or "").lower() and re.search(r"explorerthe|suitswalk|drinkcruise|classic icebreaker experience", lower):
            continue

        text = polish_inclusion_item(clean_include_item(text, title), title)
        if text and text not in clean_items:
            clean_items.append(text)

    merged_items = []
    for item in polish_inclusion_items(clean_items, title):
        lower = item.lower().strip(" .")
        if merged_items:
            prev_lower = merged_items[-1].lower()
            if prev_lower.strip(" .") == "authorized" and lower in {"english-speaker guide", "english-speaking guide", "english speaker guide"}:
                merged_items[-1] = "Authorized English-speaking guide"
                continue
            if (lower in {"boots", "gloves", "shoes", "balaclava & goggles", "balaclava and goggles"} or lower.startswith(("boots,", "gloves,", "shoes,"))) and any(marker in prev_lower for marker in ["thermal suit", "warm thermal", "boots", "gloves"]):
                merged_items[-1] = f"{merged_items[-1].rstrip(' .')}, {item}"
                continue
            if lower == "camera tripods" and "camera assistance" in prev_lower:
                merged_items[-1] = "Camera assistance and tripods"
                continue
        merged_items.append(item)

    clean_items = [_polish_activity_bullet_case(item) for item in merge_compound_inclusions(merged_items)]
    clean_items = [sanitize_inclusion_item(item, title) for item in clean_items]
    clean_items = [item for item in clean_items if item]
    if not clean_items or all(looks_like_descriptive_prose(item) for item in clean_items):
        return []
    return clean_items
