"""Compose premium client-facing activity descriptions from supplier facts.

This module deliberately does not pass supplier paragraphs through to the
renderer. It extracts useful facts (places, activity type, route focus and
logistics) and writes fresh concise itinerary prose from those facts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title, strip_price_fragments


@dataclass(slots=True)
class DescriptionDraft:
    text: str
    source: str
    warnings: list[str]


TYPO_FIXES = [
    (r"\bTIckets\b", "Tickets"),
    (r"\bIncludese\b", "Includes"),
    (r"\bBrekafast\b", "Breakfast"),
    (r"\bSupeerior\b", "Superior"),
    (r"\bTallin\b", "Tallinn"),
    (r"\bROvaniemi\b", "Rovaniemi"),
    (r"\bKriuna\b", "Kiruna"),
    (r"\bExcurssion\b", "Excursion"),
]

RAW_OR_NON_PREMIUM_PATTERNS = [
    r"\|",
    r"\bwhat are you waiting for\b",
    r"\bcome and join us\b",
    r"\bstart your adventure\b",
    r"\bbook(?:ing)?\b",
    r"\bcheck availability\b",
    r"\bprice is per\b",
    r"\bplease note\b",
    r"\bparticipanter\b",
    r"\bcarried out\b",
    r"\bmin age\b",
    r"\bcancel(?:lation)?\b",
    r"\bat checkout\b",
    r"\binstagram\b",
    r"\byour guide will be timing you\b",
    r"\bthirsty\?\b",
    r"\bjust open your mouth\b",
    r"\binstant foot wetness\b",
    r"\bguaranteed\b",
    r"\bdesigned especially for those who wish\b",
    r"\bthe best rated\b",
    r"\baward-winning\b",
    r"\btripadvisor\b",
    r"\bviator\b",
    r"\bmarketing\b",
    r"\bwalking tour by citywalk\b",
]

GENERATED_INTRO_PATTERNS = [
    r"^A planned highlight brings you into",
    r"^Your main experience today is",
    r"^The day is shaped around",
    r"gives the day a clear focus",
    r"offering a well-paced way",
]

LANDMARKS: list[tuple[str, str]] = [
    ("Hvalfjörður fjords", r"Hvalfj[öo]r[ðd]ur"),
    ("Borgarfjörður", r"Borgarfj[öo]r[ðd]ur"),
    ("Reykholt", r"Reykholt"),
    ("Deildartunguhver", r"Deildartunguhver"),
    ("Hraunfossar", r"Hraunfossar"),
    ("Barnafoss", r"Barnafoss"),
    ("Snæfellsjökull", r"Sn[æa]fellsj[öo]kull"),
    ("Gerðuberg Cliff", r"Ger[ðd]uberg"),
    ("Ytri-Tunga", r"Ytri[- ]Tunga"),
    ("Arnarstapi", r"Arnarstapi"),
    ("Djúpalónssandur", r"Dj[úu]pal[óo]nssandur"),
    ("Kirkjufell", r"Kirkjufell"),
    ("Þingvellir National Park", r"(?:Þ|Th)ingvellir"),
    ("Geysir", r"\bGeysir\b"),
    ("Strokkur", r"Strokkur"),
    ("Gullfoss", r"Gullfoss"),
    ("Brúarfoss", r"Bruarfoss|Br[úu]arfoss"),
    ("Seljalandsfoss waterfall", r"Seljalandsfoss"),
    ("Gljúfrabúi", r"Glj[úu]frab[úu]i"),
    ("Skógafoss", r"Sk[óo]gafoss"),
    ("Reynisfjara", r"Reynisfjara"),
    ("Skaftafell", r"Skaftafell"),
    ("Vatnajökull", r"Vatnaj[öo]kull|Vatnajokull"),
    ("Jökulsárlón Glacier Lagoon", r"J[öo]kuls[áa]rl[óo]n|Jokulsarlon"),
    ("Diamond Beach", r"Diamond Beach"),
    ("Blue Ice Cave", r"blue ice cave|ice cave"),
    ("Fagradalsfjall", r"Fagradalsfjall|Geldingadalir"),
    ("Blue Lagoon", r"Blue Lagoon"),
    ("Hallgrímskirkja", r"Hallgr[íi]mskirkja"),
    ("Reykjavík landmarks", r"landmarks in Reykjav[íi]k|famous landmarks"),
    ("Reykjavík street art", r"street art"),
    ("Hauganes", r"Hauganes"),
    ("Eastfjords", r"Eastfjords"),
    ("Hallormsstaðaskógar", r"Hallormssta[ðd]ask[óo]gar"),
    ("Lake Lagafljót", r"Lagaflj[óo]t"),
    ("Dettifoss waterfall", r"Dettifoss"),
    ("Mývatn", r"M[ýy]vatn"),
    ("Námskarð", r"N[áa]mskar[ðd]"),
    ("Goðafoss waterfall", r"Go[ðd]afoss"),
    ("Lava Show Reykjavík", r"Lava Show"),
    ("Nuuksio National Park", r"Nuuksio"),
    ("Tallinn Old Town", r"Tallinn"),
    ("Stockholm Old Town", r"Stockholm.*Old Town|Old Town.*Stockholm|Gamla Stan"),
    ("Senate Square", r"Senate Square"),
    ("Santa Claus Village", r"Santa Claus Village"),
    ("Arktikum Museum", r"Arktikum"),
    ("Korouoma Canyon", r"Korouoma"),
    ("Polar Explorer Icebreaker", r"Polar Explorer|Icebreaker"),
    ("Bothnian Bay", r"Bothnian Bay"),
    ("Abisko", r"Abisko"),
    ("Mount Nuolja", r"Nuolja"),
    ("Aurora Sky Station", r"Aurora sky station"),
    ("Kiruna", r"Kiruna"),
    ("Munch Museum", r"Munch Museum"),
    ("Mostraumen", r"Mostraumen"),
    ("Mount Fløyen", r"Fl[øo]yen|Fl[øo]ibanen"),
    ("Nordmarka forests", r"Nordmarka"),
    ("Suomenlinna", r"Suomenlinna"),
    ("Helsinki Cathedral", r"Helsinki Cathedral"),
    ("Sibelius Monument", r"Sibelius"),
]

STOP_SOURCE_SECTION_RE = re.compile(
    r"\n\s*(?:What's included|What’s included|Included With|Please note|Booking Information|Not included|Not Included|Meeting Point|Pick up / meeting point|Pick-up / meeting point|Departure:|Duration:|Suitable for:|Age limit:|Gather at:|Carried out:|Participanter:)\b",
    re.I,
)


def _clean_inline(value: object) -> str:
    text = str(value or "").replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in TYPO_FIXES:
        text = re.sub(pattern, replacement, text, flags=re.I)
    text = re.sub(r"\b2\.\s*5\s*hr\b", "2.5-hour", text, flags=re.I)
    text = re.sub(r"\b(\d+)\.\s*(\d+)\s*hr\b", r"\1.\2-hour", text, flags=re.I)
    return text.strip()


def _row_source(row: dict) -> str:
    parts = [row.get("details", ""), row.get("original_title", ""), row.get("title", "")]
    return _clean_inline("\n".join(str(part or "") for part in parts if str(part or "").strip()))


def _title(row: dict) -> str:
    raw = row.get("display_title") or row.get("title") or row.get("original_title") or "included experience"
    text = str(raw or "")
    text = re.sub(r"^\s*Day\s+\d+\s*[:\-–]\s*", "", text, flags=re.I)
    text = re.sub(r"\s*\|.*$", "", text).strip(" -:|")
    text = re.sub(r"^\s*[A-Za-zÀ-ÿ ]+\s*:\s*", "", text) if len(text.split(":", 1)[0].split()) <= 3 else text
    return polish_title(text or "included experience")


def _is_group_day(row: dict) -> bool:
    src = str(row.get("details") or row.get("original_title") or row.get("title") or "")
    return bool(re.match(r"^\s*Day\s+\d+\s*[:\-–]", src, flags=re.I))


def _narrative_source(row: dict) -> str:
    source = _row_source(row)
    # Prefer narrative sections when present, then strip heading/metadata.
    for marker in [r"What to expect\??", r"Overview", r"Highlights"]:
        match = re.search(marker + r"\s*(.+)", source, flags=re.I | re.S)
        if match:
            source = match.group(1)
            break
    source = re.sub(r"^\s*Day\s+\d+\s*[:\-–]\s*[^\n]+", "", source, count=1, flags=re.I).strip()
    source = STOP_SOURCE_SECTION_RE.split(source, maxsplit=1)[0]
    # Remove leading pipe metadata lines.
    if "|" in source.split("\n", 1)[0]:
        parts = [p.strip() for p in re.split(r"\s*\|\s*", source) if p.strip()]
        source = " ".join(p for p in parts if len(p.split()) > 7 and not re.search(r"\b(?:time|hrs?|meeting|includes?|tickets? only)\b", p, re.I))
    return source.strip()


def _extract_landmarks(text: str, *, limit: int = 7) -> list[str]:
    found: list[str] = []
    for label, pattern in LANDMARKS:
        if re.search(pattern, text, flags=re.I) and label not in found:
            found.append(label)
        if len(found) >= limit:
            break
    return found


def _extract_inclusion_facts(row: dict, *, limit: int = 5) -> list[str]:
    facts: list[str] = []
    for raw in row.get("includes", []) or []:
        item = _clean_inline(raw).strip(" •-*|:.")
        if not item:
            continue
        lower = item.lower()
        if any(skip in lower for skip in ["pick-up", "drop-off", "transfer", "transport", "wifi", "wi-fi", "fees", "taxes", "ticket", "guide", "photography"]):
            continue
        item = re.sub(r"\bwith transfers?\b", "", item, flags=re.I).strip(" ,-:.")
        if item and item not in facts:
            facts.append(polish_client_text(item).strip(" ."))
        if len(facts) >= limit:
            break
    return facts


def _join(items: Iterable[str], *, max_items: int = 5) -> str:
    clean = [str(item).strip(" .") for item in items if str(item).strip(" .")]
    clean = clean[:max_items]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return ", ".join(clean[:-1]) + f" and {clean[-1]}"


def _focus_from_title(title: str) -> str:
    t = re.sub(r"^(Explore|Discover|Hike|Visit|Experience|Enjoy|Watch)\s+", "", title, flags=re.I).strip()
    lower = t.lower()
    if "borgarfjör" in lower or "borgarfjord" in lower:
        return "the Borgarfjörður region and its waterfalls"
    if "snæfellsnes" in lower or "snaefellsnes" in lower:
        return "the Snæfellsnes Peninsula"
    if "golden circle" in lower:
        return "the Golden Circle"
    if "south coast" in lower and "glacier" in lower:
        return "the South Coast waterfalls and glacier landscape"
    if "jökulsárlón" in lower or "jokulsarlon" in lower:
        return "Jökulsárlón Glacier Lagoon, Diamond Beach and the ice cave landscape"
    if "eastfjords" in lower:
        return "the Eastfjords and local life"
    if "north iceland" in lower:
        return "North Iceland"
    if "whale" in lower:
        return "Whale Watching"
    if "blue lagoon" in lower and "volcano" in lower:
        return "the Fagradalsfjall volcano area and the Blue Lagoon"
    return t[:1].lower() + t[1:] if t else "the day’s main experience"


def _has_bad_residue(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in RAW_OR_NON_PREMIUM_PATTERNS)


def _compose_group_day(row: dict, source: str, title: str, city: str) -> str:
    places = _extract_landmarks(source, limit=8)
    focus = _focus_from_title(title)
    region = canonicalize_place_name(row.get("city", "")) or city or "the region"
    full = f"{title} {source}".lower()

    if "whale" in full and "hauganes" in full:
        return polish_client_text(
            "Today your guided group tour travels to Hauganes for the included Whale Watching experience. "
            "After time on the water looking for marine life, the route continues back to Reykjavík for the end of the guided programme."
        )

    if places:
        place_sentence = f"The route highlights {_join(places, max_items=6)}, giving the day a clear sense of place without rushing the experience."
    else:
        place_sentence = "The route, guided stops and overnight arrangements are handled as part of the programme, keeping the day easy to follow."
    if places:
        return polish_client_text(
            f"Today your guided group tour continues through {region}, with the day focused on {focus}. "
            f"{place_sentence}"
        )
    return polish_client_text(
        f"Today your guided group tour continues through {region}, with the day focused on {focus}. "
        f"Travel with your guide through the key landscapes and cultural stops before continuing to your overnight stay."
    )


def _compose_known_activity(row: dict, source: str, title: str, city: str) -> str:
    full = f"{title} {source} {' '.join(row.get('includes', []) or [])}".lower()
    places = _extract_landmarks(source + " " + " ".join(row.get("includes", []) or []), limit=6)
    inclusions = _extract_inclusion_facts(row, limit=4)
    city_phrase = f" in {city}" if city and city.lower() not in title.lower() else ""

    if "food" in full and "culture" in full and "bergen" in full:
        return "Explore Bergen through local food and cultural stories, with tasting stops arranged along a guided route through the city."
    if "whale watching" in full or "whale watching from downtown" in full:
        return "Set out from Reykjavík’s harbour for a whale watching experience, with onboard viewing areas and guidance while you look for marine life along the Icelandic coast."

    if "food tour" in full or "secret food" in full or "smørrebrød" in full or "smorrebrod" in full:
        if "copenhagen" in full or "smørrebrød" in full or "smorrebrod" in full or "danish meatballs" in full:
            return polish_client_text(f"Enjoy a guided food tour{city_phrase}, tasting local favourites such as smørrebrød, Danish meatballs and sweet bakery specialities while getting a flavour of the city’s food culture.")
        if "oslo" in full or city.lower() == "oslo":
            return "Explore Oslo through its food culture, with a guided route linking local flavours, hidden neighbourhood gems and stories from the city along the way."
        if "bergen" in full or city.lower() == "bergen":
            return "Explore Bergen through local food and cultural stories, with tasting stops arranged along a guided route through the city."
        return polish_client_text(f"Enjoy a guided food tour{city_phrase}, with tasting stops and local context arranged as part of the experience.")
    if "grand day trip" in full and "copenhagen" in full:
        return "Spend the day outside central Copenhagen with a guided route to Kronborg Castle, Frederiksborg Palace, Roskilde Cathedral and the Viking Ship Museum. The experience combines royal history, cultural landmarks and comfortable arranged transport."
    if "silfra" in full and ("snork" in full or "drysuit" in full):
        return "Experience the clear glacial water of Silfra on a guided drysuit snorkelling tour, with the required equipment and park arrangements included for the excursion."
    if "atv" in full or "quad" in full:
        return "Set out on a guided ATV adventure, with equipment provided and the route arranged around the surrounding black-sand and coastal landscapes."
    if "munch" in full and "museum" in full:
        return "Visit the Munch Museum at your own pace, with pre-arranged admission giving you time to explore the galleries and exhibitions independently."
    if "fløibanen" in full or "floibanen" in full:
        return "Use your round-trip Fløibanen ticket for a flexible visit to Mount Fløyen, with time to enjoy the viewpoint above Bergen during the day."
    if "fjellheisen" in full or ("round trip ticket" in full and "trom" in full):
        return "Use your round-trip Fjellheisen ticket for a flexible visit above Tromsø, with time to enjoy the panoramic views over the city, fjords and surrounding mountains."
    if "blue lagoon" in full and "volcano" in full:
        return "Begin with a guided visit to the Fagradalsfjall volcano area before ending the day in the warm geothermal waters of the Blue Lagoon. The experience balances dramatic volcanic scenery with time to relax."
    if "lava show" in full:
        return "Experience Icelandic volcanism up close during the Lava Show, where real molten lava is presented in a safe indoor setting with expert commentary."
    if "walking tour" in full or "citywalk" in full or "on foot" in full:
        safe_places = [place for place in places if not (place == "Tallinn Old Town" and "tallinn" not in full)]
        if "stockholm" in full and "old town" in full and "Stockholm Old Town" not in safe_places:
            safe_places.insert(0, "Stockholm Old Town")
        if safe_places:
            return polish_client_text(f"Set out on a guided walking tour{city_phrase}, with the route introducing {_join(safe_places, max_items=4)} alongside local stories and practical tips.")
        return polish_client_text(f"Set out on a guided walking tour{city_phrase}, with local stories, landmarks and practical tips introduced at an easy pace.")
    if "abisko" in full or "mountain hike" in full:
        return "Travel into the Abisko mountain landscape for a guided hike, with wide views, local nature stories and an included food stop along the route."
    if "korouoma" in full:
        return "Follow a guided hike through Korouoma Canyon, where frozen waterfalls, winter forest scenery and a warm outdoor food stop shape the experience."

    if "santa claus" in full and "friends" in full:
        return "Experience a festive family-friendly visit with Santa Claus, reindeer and elves, including seasonal activities, warm refreshments and time for a private Santa meeting where included."
    if "husky" in full and "reindeer" in full:
        return polish_client_text(f"Spend the day around Arctic animal experiences{city_phrase}, combining husky and reindeer encounters with time at Santa Claus Village where included.")
    if "husky" in full:
        return polish_client_text(f"Meet the huskies{city_phrase} and enjoy an active Arctic experience arranged around the season and local conditions.")
    if "reindeer" in full:
        return polish_client_text(f"Meet and feed reindeer{city_phrase}, with time to learn more about this classic Lapland experience at an easy pace.")
    if "northern lights" in full or "aurora" in full:
        return polish_client_text(f"Head out in search of the Northern Lights{city_phrase}, with the route adapted to the evening conditions and local guidance included.")
    if "tallinn" in full:
        return "Travel between Helsinki and Tallinn by ferry, with time arranged to experience the historic Old Town and its key viewpoints on foot."
    if "icebreaker" in full:
        return "Experience the Polar Explorer Icebreaker in Lapland, with the day centred on the frozen sea, Arctic scenery and the included icebreaker activities."
    if "husky" in full and "reindeer" in full:
        return polish_client_text(f"Spend the day around Arctic animal experiences{city_phrase}, combining husky and reindeer encounters with time at Santa Claus Village where included.")
    if "korouoma" in full:
        return "Follow a guided hike through Korouoma Canyon, where frozen waterfalls, winter forest scenery and a warm outdoor food stop shape the experience."
    if "abisko" in full or "mountain hike" in full:
        return "Travel into the Abisko mountain landscape for a guided hike, with wide views, local nature stories and an included food stop along the route."
    if "hike" in full or "hiking" in full or "nordmarka" in full:
        if "oslofjord" in full or "oslo fjord" in full or "nordmarka" in full:
            return "Follow a guided nature hike through the Nordmarka forest area, with local insight and viewpoints towards the Oslofjord forming the focus of the experience."
        return polish_client_text(f"Enjoy a guided hike{city_phrase}, with the route focused on local nature, scenery and a comfortable outdoor pace.")
    if "fjord" in full or "mostraumen" in full or "cruise" in full:
        if places:
            return polish_client_text(f"Enjoy a scenic water-based experience{city_phrase}, with the route focused on {_join(places, max_items=4)} and the surrounding landscapes.")
        return polish_client_text(f"Enjoy a scenic water-based experience{city_phrase}, adding a different perspective to the day’s route and landscapes.")
    if places:
        return polish_client_text(f"Enjoy {title}{city_phrase}, with the experience centred around {_join(places, max_items=5)}. The arrangements are prepared in advance so the day stays clear and easy to follow.")
    if inclusions:
        return polish_client_text(f"Enjoy {title}{city_phrase}, with the practical arrangements handled in advance and the included elements supporting a smooth experience.")
    return ""


def _fallback_description(row: dict, title: str, city: str) -> str:
    city_phrase = f" in {city}" if city and city.lower() not in title.lower() else ""
    lower = f"{title} {_row_source(row)}".lower()
    if "train" in lower or "rail" in lower:
        return polish_client_text(f"Continue by rail towards {city or 'your next destination'}, with the route and timing arranged as part of the day.")
    if "transfer" in lower or "self" in lower:
        return polish_client_text(f"Today’s travel arrangements{city_phrase} are kept clear and easy to follow, giving you a smooth transition to the next part of the journey.")
    return polish_client_text(f"Enjoy {title}{city_phrase}, with the schedule arranged to keep the experience clear, comfortable and easy to follow.")


def compose_activity_description(row: dict, fallback: str = "") -> DescriptionDraft:
    """Return a freshly composed client-facing description.

    The returned text is intentionally new prose derived from facts. It should
    not be a direct supplier paragraph unless the source is already short,
    clean and client-ready.
    """

    title = _title(row)
    city = canonicalize_place_name(row.get("city", ""))
    source = _narrative_source(row)
    warnings: list[str] = []

    if _is_group_day(row):
        text = _compose_group_day(row, source, title, city)
        return DescriptionDraft(text=text, source="composed_group_day", warnings=warnings)

    text = _compose_known_activity(row, source, title, city)
    if not text and fallback:
        # Keep fallback only if it is already clean and specific. Otherwise compose generic.
        fb = polish_client_text(_clean_inline(strip_price_fragments(fallback)))
        if fb and not _has_bad_residue(fb) and not any(re.search(p, fb, re.I) for p in GENERATED_INTRO_PATTERNS):
            # Still keep short and polished.
            sentences = re.split(r"(?<=[.!?])\s+", fb)
            text = polish_client_text(" ".join(sentences[:2]))
            warnings.append("clean_fallback_used")
    if not text:
        text = _fallback_description(row, title, city)
        warnings.append("generic_composed_fallback")

    if _has_bad_residue(text):
        warnings.append("non_premium_residue_removed")
        text = _fallback_description(row, title, city)
    return DescriptionDraft(text=polish_client_text(text), source="composed_activity", warnings=warnings)
