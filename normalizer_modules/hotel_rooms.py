"""Room-category and bed-type extraction and normalization."""

import re

from normalizer_modules.text_utils import clean_space
from text_polish import polish_client_text

ROOM_UNIT_PATTERN = r"(?:rooms?|igloos?|nests?|suites?|cabins?|apartments?|villas?|cottages?|lodges?)"
ROOM_DESCRIPTOR_PATTERN = r"(?:standard|std\.?|superior|deluxe|small glass|glass|panorama|triple|tirple|double|single|twin|family|premium|junior|classic|atrium view|large|art|waterfront view|one bedroom|two bedroom|three bedroom|four bedroom|aurora|aurora nest|log|arctic treehouse|fisherman[’']?s?)"


def _strip_bed_fragments(value: str) -> str:
    """Remove bed-count fragments that belong in the bed suffix, not the room name."""

    text = clean_space(value)
    text = re.sub(
        r"\s*(?:[-,;]|\bwith\b)?\s*(?:\d+\s*x\s*)?(?:twin\s+sofa\s+bed|single\s+sofa\s+bed|sofa\s+bed|twin\s+beds?|single\s+beds?|double\s+beds?|queen\s+bed|king\s+bed|bunk\s+bed)s?\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return clean_space(text.strip(" ,-"))


def _normalise_bed_label(label: str, quantity: str = "") -> str:
    bed = clean_space(label).lower()
    bed = re.sub(r"\btwin\s+sofa\s+bed\b", "single sofa bed", bed, flags=re.IGNORECASE)
    bed = re.sub(r"\bsingle\s+sofa\s+bed\b", "single sofa bed", bed, flags=re.IGNORECASE)
    if quantity:
        try:
            amount = int(quantity)
        except ValueError:
            amount = 0
        if amount > 1 and not bed.endswith("s"):
            bed += "s"
        return f"{amount} x {bed}" if amount else bed
    return bed


def _normalize_single_room_category(value: str, *, preserve_quantity: bool = False) -> str:
    original, room = str(value or ""), polish_client_text(value)
    if re.search(r"\bpremium\s+double\s+igloo\b", original, flags=re.IGNORECASE) and not re.search(r"\bpremium\s+double\s+igloo\b", room, flags=re.IGNORECASE):
        room = re.sub(r"\bdouble\s+igloo\b", "Premium Double Igloo", room, flags=re.IGNORECASE)
    room = re.sub(r"\bNorthern Lights\s+Nest\b", "Aurora Nest", room, flags=re.IGNORECASE)
    quantity_match = re.match(r"^\s*(\d+)\s*x\s*", room, flags=re.IGNORECASE)
    quantity = f"{quantity_match.group(1)} x" if quantity_match else ""
    room = re.sub(r"^\s*\d+\s*x\s*", "", room, flags=re.IGNORECASE)
    replacements = (
        (r"\bTirple\b", "Triple"), (r"\bStd\.?\b", "Standard"), (r"\bStandard\.\s+", "Standard "),
        (r"\s*\((?:or\s+)?accessible rooms?\)\s*", ""), (r"\bStandard\s+rooms?\b", "Standard Room"),
        (r"\bStandard\s+Double\s+rooms?\b", "Standard Double Room"), (r"\bSingle\s+rooms?\b", "Single Room"),
        (r"\bTwin\s+rooms?\b", "Twin Room"), (r"\bTriple\s+rooms?\b", "Triple Room"), (r"\bFamily\s+rooms?\b", "Family Room"),
        (r"\bJunior\s+suites?\b", "Junior Suite"), (r"\bPanorama\s+suites?\b", "Panorama Suite"),
        (r"\bSmall\s+Glass\s+Igloo\b", "Small Glass Igloo"), (r"\bWest\s+or\s+east\s+Village\b", "West or East Village"),
        (r"\bAurora\s+Nests?\b", "Aurora Nest"), (r"\bSmall Glass Igloo\s+(West or East Village)\b", r"Small Glass Igloo, \1"),
    )
    for pattern, replacement in replacements: room = re.sub(pattern, replacement, room, flags=re.IGNORECASE)
    room = clean_space(room.strip(" ,-"))
    for plural, singular in (("Rooms", "Room"), ("room", "Room"), ("Suites", "Suite"), ("suite", "Suite"), ("Cabins", "Cabin"), ("cabin", "Cabin"), ("Apartments", "Apartment"), ("apartment", "Apartment"), ("Villas", "Villa"), ("villa", "Villa"), ("Cottages", "Cottage"), ("cottage", "Cottage"), ("Lodges", "Lodge"), ("lodge", "Lodge")):
        room = re.sub(rf"\b{plural}\b", singular, room, flags=re.IGNORECASE)
    for number in ("One", "Two", "Three", "Four"): room = re.sub(rf"\b{number}\s+Bedroom\b", f"{number} Bedroom", room, flags=re.IGNORECASE)
    return f"{quantity} {room}" if preserve_quantity and quantity else room


def room_fragment_candidates(value: str) -> list[str]:
    text = re.sub(r"(?i)(room|suite|cabin|igloo)\s+(?=\d+\s*x)", r"\1, ", clean_space(value))
    parts = [clean_space(part) for part in re.split(r"\s+-\s+(?=\d+\s*x)|\s*[,|;]\s*", text) if clean_space(part)]
    result = []
    for part in parts:
        match = re.search(r"\d+\s*x\s*", part, flags=re.IGNORECASE)
        result.append(clean_space(part[match.start():] if match and match.start() > 0 else part))
    return result


def normalize_room_category(value: str) -> str:
    original, room = str(value or ""), polish_client_text(value)
    if re.search(r"\bpremium\s+double\s+igloo\b", original, flags=re.IGNORECASE) and not re.search(r"\bpremium\s+double\s+igloo\b", room, flags=re.IGNORECASE): room = re.sub(r"\bdouble\s+igloo\b", "Premium Double Igloo", room, flags=re.IGNORECASE)
    room = re.sub(r"\bNorthern Lights\s+Nest\b", "Aurora Nest", room, flags=re.IGNORECASE)
    room = re.sub(r"\bTirple\b", "Triple", room, flags=re.IGNORECASE)
    room = re.sub(r"(?<=\D)(\d+\s*x\s*)", r" \1", room, flags=re.IGNORECASE)
    if re.search(r"\b(?:night|ngiht|nite|nt)'?s?\b", room, flags=re.IGNORECASE): return ""
    pattern = re.compile(rf"^(\d+\s*x\s*)?(.+?\b{ROOM_UNIT_PATTERN}\b(?:\s+with\s+[^,|;()]+)?(?:\s*\([^)]*\))?(?:\s*\-\s*(?:Triple|Double|Single|Twin))?(?:\s+(?:west\s+or\s+east|east\s+or\s+west)\s+Village)?)", flags=re.IGNORECASE)
    matches = []
    for fragment in room_fragment_candidates(room) or [room]:
        if not re.search(rf"\b{ROOM_UNIT_PATTERN}\b", fragment, flags=re.IGNORECASE): continue
        match = pattern.search(fragment)
        if not match: continue
        quantity, category = clean_space(match.group(1) or ""), clean_space(match.group(2) or "")
        cleaned = _normalize_single_room_category(f"{quantity} {category}".strip(), preserve_quantity=bool(quantity))
        if cleaned: matches.append(cleaned)
    result = ", ".join(dict.fromkeys(matches)) if matches else _normalize_single_room_category(room, preserve_quantity=True)
    # Keep occupancy/category suffixes such as "Standard Room - Triple".  They
    # are supplier-owned room facts, not bed fragments.  Bed counts are removed
    # separately by _strip_bed_fragments()/extract_bed_type_from_source().
    return result


def _strip_occupancy_suffix_when_beds_are_explicit(room: str, source_fragment: str) -> str:
    """Remove category suffixes like "- Double" when the same fragment says "Double bed"."""

    source_lower = source_fragment.lower()
    if not re.search(r"\b(?:double|twin|single)\s+beds?\b", source_lower):
        return room
    return clean_space(re.sub(r"\s+-\s+(?:Double|Twin|Single)\s*$", "", room, flags=re.IGNORECASE))


def extract_room_category_from_source(source: str) -> str:
    matches = []
    for fragment in room_fragment_candidates(source):
        lower = fragment.lower()
        if "hotel" in lower and not re.search(r"\d+\s*x", lower): continue
        if not re.search(rf"\b{ROOM_UNIT_PATTERN}\b", fragment, flags=re.IGNORECASE): continue
        if not (re.search(r"\d+\s*x", fragment, flags=re.IGNORECASE) or re.search(ROOM_DESCRIPTOR_PATTERN, fragment, flags=re.IGNORECASE)): continue
        cleaned = _strip_bed_fragments(normalize_room_category(fragment))
        cleaned = _strip_occupancy_suffix_when_beds_are_explicit(cleaned, fragment)
        if cleaned: matches.append(cleaned)
    return ", ".join(dict.fromkeys(matches))


def extract_bed_type_from_source(source: str) -> str:
    text = re.sub(r"\bextra\s+bed\s+not\s+included\b", "", clean_space(source), flags=re.IGNORECASE)
    beds = []
    seen = set()
    pattern = r"(?:(\d+)\s*x?\s*)?\b(full\s+double\s+bed|double\s+beds?|twin\s+sofa\s+bed|single\s+sofa\s+bed|twin\s+beds?|queen\s+bed|king\s+bed|single\s+beds?|sofa\s+bed|bunk\s+bed)\b"
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        bed = _normalise_bed_label(match.group(2), match.group(1) or "")
        key = bed.lower()
        if key not in seen:
            seen.add(key)
            beds.append(bed)
    return " and ".join(beds)
