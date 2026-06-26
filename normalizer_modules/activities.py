"""Activity title normalization helpers."""

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_title
from itinerary_generation.title_cleanup import clean_client_title
from normalizer_modules.text_utils import text_blob, _lower_key
from itinerary_generation.tallinn import is_tallinn_ferry_framework, is_tallinn_old_town_guided_tour
from itinerary_generation.activity_products import fingerprint_activity

def _is_group_tour_overview(row: dict) -> bool:
    text = text_blob(row).lower()
    return (row.get("type") == "Day Overview" or row.get("effective_type") == "Day Overview") and any(
        marker in text for marker in ["group tour", "holiday package", "sharing room basis"]
    )

def looks_like_departure_text(value: str) -> bool:
    lower = _lower_key(value)
    markers = [
        "check out",
        "transfer to the airport",
        "drop at the airport",
        "return flight",
        "bound for home",
        "departure home",
        "onward flight",
        "packed breakfast",
    ]
    return sum(1 for marker in markers if marker in lower) >= 2 or ("return flight" in lower and "airport" in lower)

def _extract_supplier_day_heading(source: str) -> str:
    """Extract the supplier's real day heading from long group-tour prose.

    Group-tour activity rows often start with "Day 2: Explore ..." and then
    continue with several paragraphs. The title must come from that first
    heading, not from generic fallback tags or later marketing prose.
    """
    text = str(source or "").strip()
    if not text:
        return ""
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    match = re.match(r"^Day\s+\d+\s*[:\-–]\s*(.+)$", first_line, flags=re.IGNORECASE)
    if not match:
        return ""
    heading = re.split(r"\s{2,}|\s+Overview\b|\s+What's included\b|\s+What’s included\b|\s+What to expect\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
    heading = re.split(
        r"\s+(?:Embark|After\s+a|After\s+breakfast|Start\s+your|Continuing|Continue\s+your|"
        r"The\s+highlight|Your\s+adventure\s+begins|On\s+the\s+final|Finally|After\s+\w+|We start|"
        r"You will|You are|Prepare to|The first|A \d|At \w+|Once you|Afterwards|On your way)\b",
        heading,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    heading = heading.strip(" -:|.,")
    if not heading:
        return ""
    if re.search(r"J[öo]kuls[áa]rl[óo]n", heading, flags=re.IGNORECASE) and "ice" in heading.lower():
        heading = "Explore Jökulsárlón Glacier Lagoon & Ice Caves"
    return polish_title(heading)



def looks_like_leisure_activity(row: dict) -> bool:
    """Return True when an Activity-typed row is really free time/leisure.

    Real spreadsheets sometimes put ``Spend time at leisure`` in the Activity
    column. Those rows should shape the day flow, not become fake featured
    experiences or activity inclusions.
    """

    source_text = text_blob(row)
    lower = source_text.lower()
    # Supplier group-tour day rows often contain phrases such as "free time"
    # or "at your own pace" inside a real guided day description.  A clean
    # supplier heading ("Day 2: Discover Glaciers...") is a high-confidence
    # signal that this is an included programme day, not leisure.
    if _extract_supplier_day_heading(row.get("original_title") or row.get("details") or source_text):
        return False
    if re.search(r"\bday\s+\d+\s*[:\-–]", source_text, flags=re.IGNORECASE):
        return False

    leisure_markers = [
        "spend time at leisure",
        "leisure day",
        "day at leisure",
        "morning at leisure",
        "afternoon at leisure",
        "evening at leisure",
        "time at leisure",
        "at leisure",
        "free time",
        "at your own pace",
    ]
    if not any(marker in lower for marker in leisure_markers):
        return False
    arranged_payload = bool(row.get("time") or row.get("duration") or row.get("meeting_point") or row.get("includes"))
    arranged_payload = arranged_payload or any(marker in lower for marker in ["ticket", "tickets", "admission", "includes:", "what's included", "what’s included"])

    arranged_group_tour_markers = [
        "ice cave", "glacier", "glacial lagoon", "jökulsárlón", "jokulsarlon",
        "diamond beach", "waterfall", "geyser", "geysir", "gullfoss",
        "national park", "golden circle", "south coast", "eastfjords",
        "mývatn", "myvatn", "dettifoss", "goðafoss", "godafoss",
        "geothermal", "hot spring", "blue lagoon", "vök baths", "vok baths",
        "whale watching", "puffin", "snæfellsnes", "snaefellsnes",
    ]
    if any(marker in lower for marker in arranged_group_tour_markers):
        return False

    independent_markers = [
        "self-guided", "self guided", "explore independently", "independent walk",
        "independent stroll", "at your own pace", "own pace",
    ]
    if any(marker in lower for marker in independent_markers) and not arranged_payload:
        return True

    activity_markers = [
        "guided tour", "guided walking", "museum", "safari", "cruise", "ferry", "train",
        "flight", "coach", "northern lights", "whale", "snowmobile", "husky",
        "reindeer", "food tour", "walking tour", "tickets", "admission",
    ]
    # Rows that include one of these terms may be an actual arranged activity
    # with some leisure wording in the description. Keep those as activities.
    return not any(marker in lower for marker in activity_markers)

def normalize_activity_title(row: dict) -> str:
    source = text_blob(row)
    lower = source.lower()
    city = canonicalize_place_name(row.get("city", ""))

    supplier_day_heading = ""
    for heading_source in (row.get("original_title"), row.get("details"), source):
        supplier_day_heading = _extract_supplier_day_heading(heading_source or "")
        if supplier_day_heading:
            break
    if supplier_day_heading:
        return supplier_day_heading

    if looks_like_departure_text(source):
        return f"Departure from {city}" if city else "Departure"

    product = fingerprint_activity(row)
    if product and product.display_title:
        row["activity_product"] = product.as_row_metadata
        if product.route_legs:
            row["route_legs"] = [dict(leg) for leg in product.route_legs]
        return product.display_title

    if ("aurora" in lower or "northern light" in lower) and "reindeer" in lower and ("hunt" in lower or "hunting" in lower or "chase" in lower):
        return "Northern Lights Hunt by Reindeer"
    if "tallin" in lower or "tallinn" in lower:
        if is_tallinn_old_town_guided_tour(row):
            return "Old Town Guided Tour"
        if is_tallinn_ferry_framework(row):
            return "Day Excursion to Tallinn"
        return "Day Trip to Tallinn"
    if "fjellheisen" in lower or ("trom" in lower and any(marker in lower for marker in ["cable car", "gondola", "mountain lift"])):
        return "Fjellheisen Cable Car"
    if "round trip ticket" in lower and "trom" in lower:
        return "Round-trip viewpoint ticket in Tromsø"
    if "essential oslo" in lower or ("oslo" in lower and "city center guided walking tour" in lower):
        return "Oslo City Center Walking Tour"
    if "must-see bergen" in lower or ("bergen" in lower and "foot and boat" in lower):
        return "Bergen Walking & Boat Tour"
    if "santa claus village" in lower and ("reindeer" in lower or "safari" in lower):
        if "snowmobile" in lower or "snowmobiles" in lower:
            return "Santa Claus Village by Snowmobile & Reindeer Sleigh"
        if "husky" in lower:
            return "City Highlights, Santa Claus Village & Husky-Reindeer Safari"
        return "Santa Claus Village & Reindeer Visit"
    if "guided city tour" in lower and "narvik" in lower:
        return "Narvik Guided City Tour"
    if "ice bar" in lower and ("kiruna" in lower or "jukkasjärvi" in lower or "gällivare" in lower or "gallivare" in lower):
        return "Icehotel, Kiruna & Gällivare Touring Day"
    if "trom" in lower and "city sightseeing" in lower:
        if "aurora" in lower or "northern light" in lower:
            return "Tromsø City Sightseeing & Northern Lights Chase"
        return "Tromsø City Sightseeing"
    if "arctic wildlife" in lower and "ranua" in lower:
        return "Arctic Wildlife Adventure to Ranua Park"
    if "guided walking tour of helsinki" in lower or ("helsinki" in lower and "guided walking tour" in lower):
        return "Helsinki Guided Walking Tour"
    if "lofoten" in lower and "trollfjord" in lower:
        return "Lofoten Day Tour & Trollfjord Cruise"
    if "crystal lavvo" in lower or ("lyngen" in lower and "lavvo" in lower):
        return "Lyngen Alps Crystal Lavvo Stay"
    if "arctic route" in lower or ("senja" in lower and "coach" in lower):
        # Arctic Route bus wording can appear inside complex overnight activities.
        # Only classify the whole row as a coach transfer when the row is truly transport-like.
        if not any(marker in lower for marker in ["crystal lavvo", "overnight stay", "private crystal", "snowshoe", "basecamp"]):
            return "Arctic Route Coach Transfer"
    if "wildlife photography" in lower and "longyearbyen" in lower:
        return "Wildlife Photography Around Longyearbyen"
    if "wildlife and glacier" in lower:
        return "Wildlife & Glacier Experience"
    if "mountain hike" in lower and "abisko" in lower:
        return "Mountain Hike in Abisko"
    if "hop" in lower and "off" in lower and "bus" in lower:
        if "bergen" in lower:
            return "Bergen Hop-On Hop-Off Bus Ticket"
        if "copenhagen" in lower:
            return "Copenhagen Hop-On Hop-Off Bus Ticket"
        return "Hop-On Hop-Off Bus Ticket"

    # Fix "Private" or time-string titles from pipe-formatted rows
    raw_title = row.get("title", "").strip()
    if raw_title.lower() in {"private", "private day tour", ""} and "|" in row.get("details", ""):
        detail_parts = [p.strip() for p in row.get("details", "").split("|")]
        for part in detail_parts[1:]:
            part_clean = re.sub(r"^\d+\s*(am|pm|hrs?|hour)", "", part, flags=re.IGNORECASE).strip(" -:")
            part_clean = re.sub(r"\b\d+\s*hrs?\b", "", part_clean, flags=re.IGNORECASE).strip(" -:")
            if len(part_clean) > 5 and not re.match(r"^\d", part_clean):
                return polish_title(part_clean)

    if re.match(r"^from\s+\d", raw_title.lower()) or re.match(r"^\d+\s*(am|pm)\s+to\s+\d", raw_title.lower()):
        if "sightseeing" in lower or "private" in lower:
            return f"Private Sightseeing{' in ' + city if city else ''}"
        return f"Guided Experience{' in ' + city if city else ''}"

    title = clean_client_title(row.get("title", "") or row.get("details", ""), row)
    if len(title) > 90 or title.count(".") >= 2:
        # Split only after metadata cleanup; decimal time ranges have already been removed.
        first = re.split(r"[.|]", title, maxsplit=1)[0].strip(" ,-:")
        if len(first) <= 70 and first:
            title = first
        elif city:
            title = f"Guided experience in {city}"
        else:
            title = "Guided experience"
    return polish_title(title)

