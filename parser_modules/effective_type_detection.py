"""Effective itinerary row-type detection rules."""
import re

from place_aliases import is_known_place

from parser_modules.common import *  # noqa: F401,F403
from parser_modules.detail_extractors import _looks_like_cruise_experience_text
from parser_modules.time_parsing import normalize_duration_text, normalize_time_text

def detect_effective_type(item_type, title, details):
    combined = f"{title} {details}".lower().strip()
    normalized_item_type = normalize_type(item_type)

    # Hop-on hop-off / city pass style products are client activities, not
    # transport segments, even if the word "bus" appears in the title.
    if normalized_item_type == "Activity" and any(
        marker in combined
        for marker in ["hop on", "hop-on", "hop off", "hop-off", "24 hrs ticket", "24 hour ticket"]
    ):
        return "Activity"

    # Stegastein electric minibus is a sightseeing activity from Flåm, not a
    # route transfer, even though the supplier wording contains minibus/bus.
    if normalized_item_type == "Activity" and "stegastein" in combined and any(marker in combined for marker in ["electric minibus", "electric bus", "viewpoint", "sightseeing tour"]):
        return "Activity"

    # Overnight/night-train rows are arranged rail even when the cabin text
    # contains words such as "private sleeper compartment". Detect them before
    # local/private-transfer protection.
    if normalized_item_type == "Transfer" and re.search(r"\b(?:overnight|night)\s+train\b", combined, flags=re.IGNORECASE):
        return "Train"

    # Local/private/self transfers must stay transfers even when the terminal
    # contains words like Train Station. Run this before generic train/flight
    # detection so "Self transfer to Bergen Train Station" cannot become a
    # fake train route such as "Train to Bergen".
    if normalized_item_type == "Transfer" and any(
        marker in combined
        for marker in [
            "self transfer", "self-arranged transfer", "self-guided transfer", "private",
            "hotel to", "airport to", "station to", "to hotel", "to airport",
            "to station", "to railway station", "to train station", "accommodation",
            "bus station", "bustation",
        ]
    ) and "coach transfer to" not in combined and not re.search(r"\b(bus|coach)\s*\d+\b", combined):
        return "Transfer"

    # Accommodation-relocation rows occasionally land in the Activity column.
    # Treat explicit transfer-to-igloo/stay snippets as transfer logistics so
    # the accommodation can lead the day title instead of becoming an activity.
    if normalized_item_type == "Activity" and re.search(r"\btransfer\s+to\s+(?:glass\s+)?igloo\s+stay\b|\btransfer\s+to\s+[^.]{0,40}stay\b", combined, flags=re.IGNORECASE):
        return "Transfer"

    # Attraction/ticket products can include shuttle/return-transfer logistics.
    # Keep the product as an activity unless the row is clearly a pure route.
    if normalized_item_type == "Activity" and any(
        marker in combined
        for marker in ["blue lagoon", "comfort ticket", "admission", "entry ticket", "return transfer"]
    ) and any(marker in combined for marker in ["overview", "what's included", "what to expect", "ticket", "admission", "experience"]):
        return "Activity"

    # Tallinn day excursions use ferry tickets as logistics, but the row is the
    # day trip/activity, not a ferry transfer.
    if normalized_item_type == "Activity" and "tallinn" in combined and any(
        marker in combined for marker in ["excursion", "guided tour", "self guided", "old town"]
    ):
        return "Activity"

    if "norway in a nutshell" in combined:
        return "Transport"

    if normalized_item_type == "Activity" and _looks_like_cruise_experience_text(combined):
        return "Activity"

    route_mode_match = re.search(r"\b[a-zà-ÿøåäö .'-]+\s+to\s+[a-zà-ÿøåäö .'-]+\s+(train|flight|cruise|ferry|coach|bus)\b", combined)
    if route_mode_match and normalized_item_type in {"Transfer", "Transport", "Activity"} and "private" not in combined:
        mode = route_mode_match.group(1)
        if mode == "train":
            return "Train"
        if mode == "flight":
            return "Flight"
        if mode in {"cruise", "ferry"}:
            return "Cruise" if mode == "cruise" else "Ferry"
        return "Transport"

    if re.search(r"\b(?:day\s+|overnight\s+)?train\b[^\n|]{0,40}\b[a-zà-ÿøåäö .'-]+\s+-\s+[a-zà-ÿøåäö .'-]+", combined, flags=re.IGNORECASE):
        return "Train"

    if re.search(r"\bflight\b[^\n|]{0,40}\b[a-zà-ÿøåäö .'-]+\s+-\s+[a-zà-ÿøåäö .'-]+", combined, flags=re.IGNORECASE):
        return "Flight"

    if (
        "flight to" in combined
        or combined.startswith("flight ")
        or re.search(r"\bflight\s*[:|]", combined)
        or re.search(r"\bflight\s+[a-zà-ÿøåäö\s]+\s+to\s+", combined)
    ):
        return "Flight"

    if (
        "train to" in combined
        or "train transfer" in combined
        or "express train" in combined
        or "overnight train" in combined
        or re.search(r"\btrain\s*[:|]", combined)
        or re.search(r"\btrain\s+[a-zà-ÿøåäö\s]+\s+to\s+", combined)
    ):
        return "Train"

    if "cruise to" in combined or "overnight cruise" in combined:
        return "Cruise"

    if "ferry to" in combined:
        return "Ferry"

    # For explicit activity rows, do not downgrade the activity just because the
    # supplier text mentions a bus/coach as part of the experience.
    if normalized_item_type == "Activity":
        return "Activity"

    # Long-distance coach/bus rows should remain arranged transport even when
    # the description also mentions a bus station or resort/accommodation.
    if normalized_item_type == "Transfer" and (
        re.search(r"\b(?:bus|coach)\s*[:|]", combined)
        or "coach transfer" in combined
        or "panorama coach" in combined
        or "panoramic coach" in combined
        or "long distance" in combined and ("coach" in combined or "bus" in combined)
    ) and "private" not in combined:
        return "Transport"

    # Plain private/self-guided/local transfers remain transfers even when the
    # destination text contains "bus station". Long-distance coach/bus rows can
    # still become Transport below.
    if normalized_item_type == "Transfer" and any(
        marker in combined
        for marker in [
            "self transfer", "self-guided transfer", "private",
            "hotel to", "airport to", "station to", "to hotel",
            "to airport", "to station", "accommodation", "bus station", "bustation",
        ]
    ) and "coach transfer to" not in combined and not re.search(r"\b(bus|coach)\s*\d+\b", combined):
        return "Transfer"

    if (
        "coach transfer" in combined
        or combined.startswith("bus")
        or " bus " in f" {combined} "
    ) and "private" not in combined:
        return "Transport"

    return normalized_item_type
