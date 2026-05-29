"""Activity description fallback and composition helpers."""

from __future__ import annotations

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text
from itinerary_generation.content_text import clean_inline
from itinerary_generation.description_composer import compose_activity_description
from itinerary_generation.title_cleanup import clean_admin_title_fragment, clean_client_title


def _description_from_included_items(row: dict) -> str:
    """Create a specific fallback from included sites when no prose exists."""

    title = clean_admin_title_fragment(row.get("title", "") or row.get("original_title", ""))
    includes = [clean_inline(item).strip(" .") for item in (row.get("includes", []) or []) if clean_inline(item).strip(" .")]
    lower_title = title.lower()
    include_text = " ".join(includes).lower()
    if "sky lagoon" in lower_title:
        if "7-step" in include_text or "7 step" in include_text or "ritual" in include_text:
            return "Relax at Sky Lagoon and enjoy the Saman Pass with its 7-step ritual arranged as part of the experience."
        return "Relax at Sky Lagoon, with admission arranged as part of the experience."
    if "blue lagoon" in lower_title and "volcano" not in lower_title:
        return "Enjoy time at the Blue Lagoon, with admission details arranged as part of the experience."

    useful: list[str] = []
    for item in includes:
        lower = item.lower()
        if any(skip in lower for skip in ["pick-up", "drop-off", "transfer", "transportation", "guide", "ticket", "tickets", "wifi", "wi-fi"]):
            continue
        useful.append(polish_client_text(item).strip(" ."))
        if len(useful) >= 4:
            break
    if len(useful) < 2:
        return ""
    if len(useful) == 2:
        focus = f"{useful[0]} and {useful[1]}"
    else:
        focus = ", ".join(useful[:-1]) + f" and {useful[-1]}"
    if title:
        return polish_client_text(f"This arranged experience is centred around {focus}, giving the day a clear and memorable focus.")
    return polish_client_text(f"The day includes {focus}, with the arrangements kept clear and easy to follow.")


def safe_generic_description(row: dict) -> str:
    """Last-resort client-facing description that never echoes raw supplier text."""
    title = clean_client_title(row.get("title") or row.get("original_title") or "", row)
    city = canonicalize_place_name(row.get("city", ""))
    lower = f"{title} {row.get('title','')} {row.get('details','')} {row.get('original_title','')}".lower()
    place = f" in {city}" if city else ""
    if "walking tour" in lower or "citywalk" in lower:
        return f"Enjoy a guided walking tour{place}, with local stories and key sights introduced at an easy pace."
    if "munch" in lower and "museum" in lower:
        return "Visit the Munch Museum at your own pace with pre-arranged admission tickets."
    if "fløibanen" in lower or "floibanen" in lower:
        return "Use your round-trip Fløibanen ticket for a flexible visit to Mount Fløyen, with time to enjoy the views over Bergen."
    if (
        ("cable car" in lower or "funicular" in lower or "gondola" in lower)
        and ("ticket" in lower or "admission" in lower)
        and ("view" in lower or "mountain" in lower or "viewpoint" in lower)
    ):
        return f"Use your pre-arranged ticket for a flexible visit by cable car{place}, with time to enjoy the mountain viewpoint and surrounding views during the day."
    if "blue lagoon" in lower and "volcano" in lower:
        return "Combine a guided visit to the Fagradalsfjall volcano area with time to relax in the warm geothermal waters of the Blue Lagoon."
    if "blue lagoon" in lower:
        return "Enjoy time at the Blue Lagoon, with admission arranged as part of the day."
    if (
        "photo tour" in lower
        or "photo excursion" in lower
        or "arctic landscapes" in lower
        or "scenic fjord safari" in lower
        or "camera settings" in lower
        or "nature photos" in lower
    ) and ("fjord" in lower or "landscape" in lower or "scenic" in lower):
        return f"Travel outside {city or 'the city'} on a guided photo-focused excursion through Arctic landscapes, fjords and coastal scenery."
    if "ice floating" in lower or ("floating" in lower and ("thermal" in lower or "wetsuit" in lower or "frozen lake" in lower)):
        return f"Float in a frozen lake{place}, wearing a thermal survival suit while the Arctic night sky forms the focus of the experience."
    if "northern lights" in lower or "aurora" in lower:
        return "Head out in search of the Northern Lights, with the route adapted to the evening conditions and local guidance included."
    if "ferry" in lower and "tallinn" in lower:
        return "Travel between Helsinki and Tallinn by ferry, with time arranged to experience the historic Old Town."
    if "train" in lower or "rail" in lower:
        return "Continue by rail, with the route and timing arranged as part of the day."
    if "hike" in lower or "hiking" in lower:
        return f"Enjoy a guided outdoor experience{place}, with the route planned around the scenery and pace of the day."
    return f"Enjoy a planned experience{place}, with the key arrangements prepared in advance and the wider day kept easy to follow."


def client_activity_description(row: dict, fallback: str = "") -> str:
    """Compose final client-facing activity text from facts, not supplier paragraphs."""

    draft = compose_activity_description(row, fallback=fallback)
    return draft.text
