"""Hotel and accommodation row normalization helpers."""

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_hotel_name
from normalizer_modules.text_utils import clean_space

def _normalize_single_room_category(value: str, *, preserve_quantity: bool = False) -> str:
    room = polish_client_text(value)
    quantity_match = re.match(r"^\s*(\d+)\s*x\s*", room, flags=re.IGNORECASE)
    quantity = f"{quantity_match.group(1)} x" if quantity_match else ""
    room = re.sub(r"^\s*\d+\s*x\s*", "", room, flags=re.IGNORECASE)
    room = re.sub(r"\bTirple\b", "Triple", room, flags=re.IGNORECASE)
    room = re.sub(r"\bStandard\s+room\b", "Standard Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bStandard\s+Double\s+room\b", "Standard Double Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bStandard\s+Double\s+Room\b", "Standard Double Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bSingle\s+room\b", "Single Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bTwin\s+room\b", "Twin Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bTriple\s+room\b", "Triple Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bFamily\s+room\b", "Family Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bJunior\s+suite\b", "Junior Suite", room, flags=re.IGNORECASE)
    room = re.sub(r"\bPanorama\s+suite\b", "Panorama Suite", room, flags=re.IGNORECASE)
    room = re.sub(r"\bSmall\s+Glass\s+Igloo\b", "Small Glass Igloo", room, flags=re.IGNORECASE)
    room = re.sub(r"\bWest\s+or\s+east\s+Village\b", "West or East Village", room, flags=re.IGNORECASE)
    room = re.sub(r"\bSmall Glass Igloo\s+(West or East Village)\b", r"Small Glass Igloo, \1", room, flags=re.IGNORECASE)
    room = clean_space(room.strip(" ,-"))
    if preserve_quantity and quantity:
        return f"{quantity} {room}"
    return room

ROOM_UNIT_PATTERN = r"(?:room|igloo|suite|cabin)"
ROOM_DESCRIPTOR_PATTERN = (
    r"(?:standard|superior|deluxe|small glass|glass|panorama|triple|tirple|"
    r"double|single|twin|family|premium|junior|classic|atrium view|large|art)"
)


def _room_fragment_candidates(value: str) -> list[str]:
    """Return likely room fragments without losing multiple room categories."""

    text = clean_space(value)
    text = re.sub(r"(?i)(room|suite|cabin|igloo)\s+(?=\d+\s*x)", r"\1, ", text)
    parts = [clean_space(part) for part in re.split(r"\s+-\s+(?=\d+\s*x)|\s*[,|;]\s*", text) if clean_space(part)]
    cleaned_parts = []
    for part in parts:
        quantity_match = re.search(r"\d+\s*x\s*", part, flags=re.IGNORECASE)
        if quantity_match and quantity_match.start() > 0:
            part = part[quantity_match.start():]
        cleaned_parts.append(clean_space(part))
    return cleaned_parts


def normalize_room_category(value: str) -> str:
    room = polish_client_text(value)
    room = re.sub(r"\bTirple\b", "Triple", room, flags=re.IGNORECASE)
    room = re.sub(r"(?<=\D)(\d+\s*x\s*)", r" \1", room, flags=re.IGNORECASE)
    if re.search(r"\bnight'?s?\b", room, flags=re.IGNORECASE):
        return ""

    # Preserve room quantities from source rows. Client inclusions need to show
    # "2 x Standard Room" rather than silently dropping the count.
    fragments = _room_fragment_candidates(room) or [room]
    matches = []
    room_match_pattern = re.compile(
        rf"^(\d+\s*x\s*)?(.+?\b{ROOM_UNIT_PATTERN}\b(?:\s+with\s+[^,|;()]+)?(?:\s*\([^)]*\))?(?:\s*\-\s*(?:Triple|Double|Single|Twin))?(?:\s+(?:west\s+or\s+east|east\s+or\s+west)\s+Village)?)",
        flags=re.IGNORECASE,
    )
    for fragment in fragments:
        if not re.search(rf"\b{ROOM_UNIT_PATTERN}\b", fragment, flags=re.IGNORECASE):
            continue
        room_match = room_match_pattern.search(fragment)
        if not room_match:
            continue
        quantity = clean_space(room_match.group(1) or "")
        category = clean_space(room_match.group(2) or "")
        cleaned = _normalize_single_room_category(f"{quantity} {category}".strip(), preserve_quantity=bool(quantity))
        if cleaned:
            matches.append(cleaned)

    if matches:
        deduped = []
        for match in matches:
            if match not in deduped:
                deduped.append(match)
        return ", ".join(deduped)

    return _normalize_single_room_category(room, preserve_quantity=True)


def extract_room_category_from_source(source: str) -> str:
    """Extract room text from raw hotel details, preserving quantities."""
    matches = []
    for fragment in _room_fragment_candidates(source):
        lower = fragment.lower()
        if "hotel" in lower and not re.search(r"\d+\s*x", lower):
            continue
        if not re.search(rf"\b{ROOM_UNIT_PATTERN}\b", fragment, flags=re.IGNORECASE):
            continue
        if not (
            re.search(r"\d+\s*x", fragment, flags=re.IGNORECASE)
            or re.search(ROOM_DESCRIPTOR_PATTERN, fragment, flags=re.IGNORECASE)
        ):
            continue
        cleaned = normalize_room_category(fragment)
        if cleaned:
            matches.append(cleaned)
    if matches:
        deduped = []
        for match in matches:
            if match not in deduped:
                deduped.append(match)
        return ", ".join(deduped)
    return ""

def normalize_meal_plan(value: str, source_text: str = "") -> str:
    text = f"{value} {source_text}".lower()
    if any(marker in text for marker in ["without breakfast", "without brekafast", "no breakfast", "breakfast not"]):
        return "without breakfast"
    if "breakfast" in text or "brekafast" in text or "breekfast" in text:
        if "dinner" in text:
            return "breakfast and dinner"
        return "breakfast"
    if "dinner" in text:
        return "dinner"
    return polish_client_text(value)

def extract_star_level(value: str) -> str:
    text = str(value or "")
    match = re.search(r"\b([2-5])\s*[- ]?star\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return ""

def is_placeholder_hotel_name(name: str, city: str = "") -> bool:
    text = clean_space(name)
    if not text:
        return True
    lower = text.lower()
    city_lower = clean_space(city).lower()
    if city_lower and lower in {city_lower, canonicalize_place_name(city).lower()}:
        return True
    if re.search(r"\b\d\s*[- ]?star\b", lower):
        return True
    if re.search(r"\b\d+\s*x?\s*night", lower):
        return True
    if any(marker in lower for marker in ["standard room", "standard double room", "incl breakfast", "incl brekafast", "breakfast", "room category"]):
        return True
    if lower in {"hotel", "accommodation", "or similar", "similar"}:
        return True
    return False

def clean_hotel_name_from_source(row: dict) -> str:
    source = clean_space(row.get("details", ""))
    city = clean_space(row.get("city", ""))
    source = re.sub(r"\([^)]*supplement[^)]*\)", "", source, flags=re.IGNORECASE)
    source = re.sub(r"\([^)]*upgrade[^)]*\)", "", source, flags=re.IGNORECASE)
    parts = [clean_space(part) for part in re.split(r"\s+-\s+|,|\|", source) if clean_space(part)]
    candidates = []
    hotel_brand_prefixes = ("scandic", "radisson", "comfort", "quality", "clarion", "thon", "moxy", "grand", "hotel", "santa", "kakslauttanen")

    for part in parts:
        part_clean = polish_hotel_name(part)
        lower = part_clean.lower()
        if city and lower == city.lower():
            continue
        if any(marker in lower for marker in ["check in", "check-in", "accommodation", "night stay"]):
            continue
        if re.search(r"\b\d\s*[- ]?star\b", lower):
            continue
        if re.search(r"\b\d+\s*x?\s*night", lower):
            # Some weak inputs use either "2 Night's Hotel Scandic Kemi" or
            # "Hotel Aakenus 2xNight" in the same comma fragment.
            trailing = re.sub(r"^\s*\d+\s*(?:x\s*)?night'?s?\s*", "", part_clean, flags=re.IGNORECASE).strip(" ,-:")
            trailing = re.sub(r"\s*\d+\s*(?:x\s*)?night'?s?\s*$", "", trailing, flags=re.IGNORECASE).strip(" ,-:")
            if trailing:
                part_clean = trailing
                lower = part_clean.lower()
            else:
                continue
        if any(marker in lower for marker in ["standard", "double room", "breakfast", "brekafast", "dinner"]):
            continue
        if lower.startswith("hotel ") and any(lower.startswith(f"hotel {brand}") for brand in ["scandic", "radisson", "comfort", "quality", "clarion", "thon", "moxy", "grand"]):
            part_clean = part_clean[6:].strip()
        if lower.startswith(hotel_brand_prefixes) or len(part_clean.split()) >= 2:
            candidates.append(part_clean)

    return polish_hotel_name(candidates[0]) if candidates else ""

def normalize_hotel_row(row: dict) -> dict:
    source = clean_space(row.get("details", ""))
    city = clean_space(row.get("city", ""))
    star = extract_star_level(source)

    name = polish_hotel_name(row.get("hotel_name", ""))
    if is_placeholder_hotel_name(name, city):
        detected = clean_hotel_name_from_source(row)
        if detected and not is_placeholder_hotel_name(detected, city):
            name = detected
        elif star:
            name = f"{star}-star hotel"
        else:
            name = "Centrally located hotel"

    room = normalize_room_category(row.get("room_category", ""))
    source_room = extract_room_category_from_source(source)
    if source_room and (not room or " x " in source_room.lower() or "," in source_room):
        room = source_room
    if not room:
        room = "Standard Double Room"

    nights = clean_space(row.get("hotel_nights", ""))
    if not nights:
        night_match = re.search(r"\b(\d+)\s*(?:x\s*)?night", source, flags=re.IGNORECASE)
        if night_match:
            nights = night_match.group(1)

    meal = normalize_meal_plan(row.get("meal_plan", ""), source)

    # Strip trailing city suffix that bleeds into hotel names
    # e.g. "Scandic Rovaniemi city" → "Scandic Rovaniemi"
    if city and name.lower().endswith(" city"):
        trimmed = name[:-5].strip()
        if trimmed:
            name = trimmed

    name = re.sub(r"\bSariselka\b", "Saariselkä", name, flags=re.IGNORECASE)
    row["hotel_name"] = name
    row["title"] = name
    row["room_category"] = room
    row["hotel_nights"] = nights
    row["meal_plan"] = meal
    return row

