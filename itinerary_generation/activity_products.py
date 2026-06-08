"""Activity product fingerprint catalogue.

This module centralizes high-risk activity identity decisions before rendering.
It is intentionally source-first: the returned fingerprint records the supplier
product family and safe client title without letting incidental description
landmarks rename the activity.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal

from place_aliases import canonicalize_place_name
from text_polish import polish_title
from itinerary_generation.transport_norway import (
    _is_norway_in_a_nutshell_text,
    extract_norway_nutshell_route_legs,
    extract_norway_nutshell_route_points,
)

ActivityProductConfidence = Literal["strong", "weak"]


@dataclass(frozen=True)
class ActivityProductFingerprint:
    """Canonical identity for one supplier activity product."""

    canonical_family: str
    product_type: str
    display_title: str
    confidence: ActivityProductConfidence = "strong"
    source_title: str = ""
    variant_tags: tuple[str, ...] = ()
    route_legs: tuple[dict[str, str], ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def as_row_metadata(self) -> dict[str, Any]:
        return {
            "canonical_family": self.canonical_family,
            "product_type": self.product_type,
            "display_title": self.display_title,
            "confidence": self.confidence,
            "source_title": self.source_title,
            "variant_tags": list(self.variant_tags),
            "route_legs": [dict(leg) for leg in self.route_legs],
            "warnings": list(self.warnings),
        }


_OPTIONAL_PREFIX_RE = re.compile(
    r"^\s*(?:(?:optinal|optional)\s*(?:add\s*[- ]?on|addon)?(?:\s+activity)?(?:\s+on\s+request)?|"
    r"(?:add\s*[- ]?on|addon)\s+(?:optional|optinal)(?:\s+activity)?(?:\s+at\s+addi?t?ional\s+cost)?|"
    r"optional\s+activity\s+at\s+addi?t?ional\s+cost)\s*[:|\-]*\s*",
    flags=re.IGNORECASE,
)

_ADMIN_PREFIX_RE = re.compile(
    r"^\s*(?:\d{1,2}\s+[A-Za-z]{3,9}\s*\|\s*)?"
    r"(?:mon|tue|wed|thu|fri|sat|sun)\s+\d{1,2}\s+[a-z]{3,9}\s+\d{4}\s*[:|\-]*\s*",
    flags=re.IGNORECASE,
)

_DATE_SUFFIX_RE = re.compile(
    r"\s*[:\-]?\s*(?:mon|tue|wed|thu|fri|sat|sun)\s+\d{1,2}\s+[a-z]{3,9}\s+\d{4}\s*$",
    flags=re.IGNORECASE,
)

_TIME_OR_DURATION_RE = re.compile(
    r"^(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?(?:\s*[-–—]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?|\d+(?:\.\d+)?\s*(?:hrs?|hours?|min|minutes?))$",
    flags=re.IGNORECASE,
)

_TITLE_STOP_MARKERS = (
    "overview",
    "what's included",
    "what’s included",
    "what to expect",
    "pick up / meeting point",
    "pick-up / meeting point",
    "meeting point",
    "included:",
    "includes:",
)

_TYPO_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bNUtsheel\b|\bNutsheel\b|\bNuthsell\b|\bNUtshell\b", "Nutshell"),
    (r"\bTallinnn\b|\bTallin\b", "Tallinn"),
    (r"\bHlesinkih?\b|\bHellsinki\b|\bHelisnki\b", "Helsinki"),
    (r"\bReyakjvik\b|\bReykajvik\b|\bReykavik\b|\bReykjavik\b", "Reykjavík"),
    (r"\bTromso\b", "Tromsø"),
    (r"\bAlesund\b", "Ålesund"),
    (r"\bFlam\b|\bFLam\b", "Flåm"),
    (r"\bKakslauttenen\b", "Kakslauttanen"),
    (r"\bSaariselka\b", "Saariselkä"),
    (r"\bFunicual\b", "Funicular"),
    (r"\bProfesional\b", "Professional"),
    (r"\bEngish\b", "English"),
    (r"\bticktes\b", "tickets"),
    (r"\btickert\b", "ticket"),
    (r"\bavaiable\b", "available"),
    (r"\barrnaged\b", "arranged"),
    (r"\bAfternon\b", "Afternoon"),
    (r"\bMelas\s+onboard\b", "Meals onboard"),
    (r"\bCLaus\b", "Claus"),
    (r"\bVIllage\b", "Village"),
    (r"\badditonal\b", "additional"),
)


def canonicalize_activity_text(value: str) -> str:
    """Apply shared activity typo/place cleanup to source/title fragments."""

    text = str(value or "").replace("\xa0", " ")
    for pattern, replacement in _TYPO_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def activity_product_context(row: dict | None = None, *values: object) -> str:
    """Return source text for product matching."""

    pieces: list[str] = []
    if row:
        for key in ("raw", "original_title", "title", "details", "description", "city"):
            value = row.get(key, "")
            if value:
                pieces.append(str(value))
        includes = row.get("includes") or []
        if isinstance(includes, (list, tuple, set)):
            pieces.extend(str(item) for item in includes if item)
        elif includes:
            pieces.append(str(includes))
    pieces.extend(str(value) for value in values if value)
    return canonicalize_activity_text(" ".join(pieces))




def _canonicalize_route_source(value: str) -> str:
    text = str(value or "").replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in _TYPO_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Preserve newlines because the Norway in a Nutshell timetable parser uses
    # one place/time point per line. Only compact spaces within each line.
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))


def _legs_from_route_points(points: list[str]) -> tuple[dict[str, str], ...]:
    if len(points) < 2:
        return ()
    return tuple({"origin": points[index], "destination": points[index + 1], "mode": ""} for index in range(len(points) - 1))

def _strip_optional_prefix(value: str) -> str:
    text = str(value or "").strip(" \t\"'")
    previous = None
    while previous != text:
        previous = text
        text = _OPTIONAL_PREFIX_RE.sub("", text).strip(" -:|\t")
    return text


def _strip_date_suffix(value: str) -> str:
    text = str(value or "").strip()
    text = _DATE_SUFFIX_RE.sub("", text).strip(" -:|")
    # Repair parser artifacts such as "Northern Lights photography: mon 2828 sep 20262026".
    text = re.sub(r"\s*:\s*(?:mon|tue|wed|thu|fri|sat|sun)\s+\d{2,4}\s+[a-z]{3,9}\s+\d{4,8}\s*$", "", text, flags=re.IGNORECASE).strip(" -:|")
    return text


def _clean_title_segment(segment: str) -> str:
    text = canonicalize_activity_text(segment)
    text = re.sub(
        r"\(\s*\d{1,2}\.\s*\d{2}\s*[-–—]\s*\d{1,2}\.\s*\d{2}\s*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = _strip_optional_prefix(text)
    text = _ADMIN_PREFIX_RE.sub("", text).strip(" -:|")
    text = _strip_date_suffix(text)
    for marker in _TITLE_STOP_MARKERS:
        index = text.lower().find(marker)
        if index > 0:
            text = text[:index].strip(" -:|")
    text = re.sub(r"\b(?:time|duration|departure)\s*:.*$", "", text, flags=re.IGNORECASE).strip(" -:|")
    if ":" in text and not re.search(r"\b\d{1,2}:\d{2}\b", text):
        possible_city, rest = text.split(":", 1)
        if canonicalize_place_name(possible_city.strip()) and rest.strip():
            text = rest.strip()
    return polish_title(text.strip(" -:|"))


def extract_source_product_title(row: dict | None = None, *values: object) -> str:
    """Extract the supplier product title after optional/date/admin prefixes."""

    candidates: list[str] = []
    if row:
        for key in ("title", "original_title", "details", "raw"):
            value = str(row.get(key, "") or "").strip()
            if value:
                candidates.append(value)
    candidates.extend(str(value) for value in values if value)

    for candidate in candidates:
        normalized = canonicalize_activity_text(candidate)
        normalized, removed_decimal_time = re.subn(
            r"\(\s*\d{1,2}\.\s*\d{2}\s*[-–—]\s*\d{1,2}\.\s*\d{2}\s*\)",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        if removed_decimal_time:
            normalized = re.sub(r"\s+incl\.?.*$", "", normalized, flags=re.IGNORECASE).strip()
        # Prefer pipe/dash separated product segments so "Optional addon on request | Tromsø: ..." keeps the real product.
        parts = re.split(r"\s*\|\s*|\s+-\s+", normalized)
        for index, part in enumerate(parts):
            cleaned = _clean_title_segment(part)
            if not cleaned:
                continue
            lower = cleaned.lower()
            if _TIME_OR_DURATION_RE.match(lower):
                continue
            if lower in {"optional", "optional addon", "optional add on", "on request", "activity"}:
                continue
            if lower.startswith(("day ", "__main__", "__optional__")):
                continue
            if len(cleaned) >= 4:
                return cleaned
        cleaned = _clean_title_segment(normalized)
        if cleaned and len(cleaned) >= 4 and not _TIME_OR_DURATION_RE.match(cleaned.lower()):
            return cleaned
    return ""


def _match(canonical_family: str, product_type: str, title: str, *, source_title: str = "", variant_tags: tuple[str, ...] = (), route_legs: tuple[dict[str, str], ...] = (), confidence: ActivityProductConfidence = "strong", warnings: tuple[str, ...] = ()) -> ActivityProductFingerprint:
    return ActivityProductFingerprint(
        canonical_family=canonical_family,
        product_type=product_type,
        display_title=title,
        confidence=confidence,
        source_title=source_title or title,
        variant_tags=variant_tags,
        route_legs=route_legs,
        warnings=warnings,
    )




def _direct_route_points_from_source(source: str) -> list[str]:
    city = r"Bergen|Oslo|Flåm|Flam|Voss|Gudvangen|Myrdal"
    patterns = (
        rf"\b(?P<origin>{city})\s+to\s+(?P<destination>{city})\b",
        rf"\bnorway\s+in\s+a\s+nutshell\s+(?P<origin>{city})\s+to\s+(?P<destination>{city})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if not match:
            continue
        origin = canonicalize_place_name(polish_title(match.group("origin")))
        destination = canonicalize_place_name(polish_title(match.group("destination")))
        if origin and destination and origin.lower() != destination.lower():
            return [origin, destination]
    return []


def _should_preserve_nutshell_origin(source: str) -> bool:
    city = r"Bergen|Oslo|Flåm|Flam|Voss|Gudvangen|Myrdal"
    return bool(
        re.search(rf"^\s*(?:{city})\s+to\s+(?:{city})\s*\|\s*Norway\s+in\s+a\s+Nutshell", source, flags=re.IGNORECASE)
        or re.search(rf"\b(?:Nærøyfjord|Naeroyfjord)[^\n:|]{{0,120}}\b(?:{city})\s+to\s+(?:{city})\s*(?:[:|,\-]|$)", source, flags=re.IGNORECASE)
    )


def _route_title_from_points(points: list[str], *, preserve_origin: bool = False) -> str:
    if len(points) >= 2 and preserve_origin:
        return f"Norway in a Nutshell from {polish_title(points[0])} to {polish_title(points[-1])}"
    if points:
        return f"Norway in a Nutshell to {polish_title(points[-1])}"
    return "Norway in a Nutshell"


def _northern_lights_title(source_lower: str, source_title: str) -> str:
    if "reindeer" in source_lower and any(marker in source_lower for marker in ("hunt", "hunting", "chase")):
        return "Northern Lights Hunt by Reindeer"
    if "basecamp" in source_lower or "base camp" in source_lower:
        return "Northern Lights Basecamp"
    if "cruise" in source_lower or "silent electric ship" in source_lower:
        return "Northern Lights Cruise"
    if "floating" in source_lower or "float" in source_lower:
        return "Northern Lights Ice Floating"
    if "chase" in source_lower:
        return "Northern Lights Chase"
    if "photo tour" in source_lower or "photography" in source_lower:
        return "Northern Lights Photography Tour"
    if "dinner" in source_lower:
        return "Northern Lights Dinner"
    if "hunt" in source_lower or "mileage" in source_lower:
        return "Northern Lights Hunt"
    return "Northern Lights Experience"


def _is_bergen_guided_flam_day_tour(source_lower: str) -> bool:
    """Return True for Bergen-to-Flåm guided day tours that resemble Nutshell routes.

    These supplier products include several Norway in a Nutshell ingredients
    (Flåm Railway, Nærøyfjord/fjord cruise, Gudvangen/Voss legs), but the sold
    product is a guided round-trip day tour from Bergen.  It must not be
    renamed to "Norway in a Nutshell" just because the route components overlap.
    """

    has_bergen_origin = "bergen" in source_lower
    has_flam_product = "flåm" in source_lower or "flam" in source_lower
    has_guided_day_tour = any(marker in source_lower for marker in ("guided day tour", "guided discovery", "day tour to flåm", "day tour to flam"))
    has_route_components = any(marker in source_lower for marker in ("flåm railway", "flam railway", "nærøyfjord", "naeroyfjord", "fjord cruise"))
    has_roundtrip_legs = "voss to bergen" in source_lower or "coach, voss to bergen" in source_lower or "back to bergen" in source_lower
    return has_bergen_origin and has_flam_product and has_guided_day_tour and has_route_components and has_roundtrip_legs


def _ticket_title(source_title: str, fallback: str) -> str:
    """Preserve safe ticket/admission names without leaking long supplier prose."""

    if source_title and len(source_title) <= 80:
        lower = source_title.lower()
        if any(marker in lower for marker in ("ticket", "tickets", "admission", "entrance", "museum", "tivoli", "skyview", "munch", "vasa")):
            return source_title
    return fallback


def fingerprint_activity(row: dict | None = None, *values: object) -> ActivityProductFingerprint | None:
    """Return a canonical activity product fingerprint when source evidence is strong."""

    source = activity_product_context(row, *values)
    source_lower = source.lower()
    if not source_lower:
        return None

    source_title = extract_source_product_title(row, *values)

    if _is_bergen_guided_flam_day_tour(source_lower):
        return _match(
            "bergen_guided_flam_day_tour",
            "guided_scenic_day_tour",
            "Bergen Guided Day Tour to Flåm with Flåm Railway & Fjord Cruise",
            source_title=source_title,
            variant_tags=("flam_railway", "fjord_cruise", "coach", "guided"),
        )

    if _is_norway_in_a_nutshell_text(source):
        # Use supplier route-bearing fields only. Normalized titles and generic
        # inclusion labels can otherwise feed back into the route parser and
        # create corrupted labels such as "to Bergen Oslo to Bergen".
        if row:
            route_fields = [str(row.get("details", "") or "")]
            original_title = str(row.get("original_title", "") or "")
            title = str(row.get("title", "") or "")
            # Prefer original supplier title when present. For direct unit rows
            # without original_title, include title so route-bearing supplier
            # names like "Nærøyfjord Cruise & Luggage Transfer Bergen to Oslo"
            # can preserve direction.
            route_fields.append(original_title or title)
            route_source = _canonicalize_route_source("\n".join(value for value in route_fields if value.strip()))
        else:
            route_source = _canonicalize_route_source(source)
        direct_points = _direct_route_points_from_source(route_source)
        points = extract_norway_nutshell_route_points(route_source) or direct_points
        legs = tuple(extract_norway_nutshell_route_legs(route_source)) or _legs_from_route_points(points)
        tags: list[str] = []
        if "luggage" in source_lower and ("porter" in source_lower or "service" in source_lower):
            tags.append("luggage_service")
        if "part 1" in source_lower:
            tags.append("part_1")
        if "part 2" in source_lower:
            tags.append("part_2")
        return _match(
            "norway_in_a_nutshell",
            "scenic_route",
            _route_title_from_points(points, preserve_origin=_should_preserve_nutshell_origin(route_source)),
            source_title=source_title or "Norway in a Nutshell",
            variant_tags=tuple(tags),
            route_legs=legs,
        )

    if "tallinn" in source_lower and "old town" in source_lower and "guided" in source_lower and not any(marker in source_lower for marker in ("ferry", "cruise duration", "round trip", "excursion to tallinn")):
        return _match("tallinn_old_town_guided_tour", "walking_tour", "Old Town Guided Tour", source_title=source_title)

    if "tallinn" in source_lower and ("ferry" in source_lower or "cruise duration" in source_lower or "excursion to tallinn" in source_lower):
        tags = []
        if re.search(r"\bself[-\s]*guided\b|\bfree time\b|\bself explored\b", source_lower):
            tags.append("self_guided")
        elif re.search(r"\bguided\b[^.]{0,80}\bold town\b|\bold town\b[^.]{0,80}\bguided\b", source_lower):
            tags.append("guided_old_town")
        else:
            tags.append("ferry_framework")
        return _match("day_excursion_to_tallinn", "ferry_excursion", "Day Excursion to Tallinn", source_title=source_title, variant_tags=tuple(tags))

    if "oslo" in source_lower and ("fjord cruise" in source_lower or "fjord sightseeing cruise" in source_lower or "oslo fjord" in source_lower or "oslofjord" in source_lower) and any(marker in source_lower for marker in ("electric", "silent", "sightseeing", "islands", "ship", "boat")):
        tags = []
        if "bygd" in source_lower:
            tags.append("bygdoy_stop")
        if "audio guide" in source_lower or "voice of norway" in source_lower:
            tags.append("audio_guide")
        if "island" in source_lower:
            tags.append("islands")
        if "100% electric" in source_lower or "electric" in source_lower:
            tags.append("electric_boat")
        title = source_title if source_title and "fjord" in source_title.lower() and "cruise" in source_title.lower() else ("Oslofjord Sightseeing Cruise" if "sightseeing" in source_lower else "Oslofjord Cruise with Silent Electric Ship")
        return _match("oslofjord_cruise", "fjord_cruise", title, source_title=source_title, variant_tags=tuple(tags))

    if "oslo" in source_lower and ("munch museum" in source_lower or re.search(r"\bmunch\b", source_lower)) and any(marker in source_lower for marker in ("ticket", "tickets", "entrance", "entry", "admission", "museum")):
        return _match("munch_museum_ticket", "admission", "Munch Museum Visit", source_title=source_title)

    if "bergen" in source_lower and "city drive" in source_lower:
        return _match("bergen_city_drive", "private_drive", source_title if source_title else "Private Bergen City Drive", source_title=source_title)

    if "fløibanen" in source_lower or "floibanen" in source_lower or "funicular" in source_lower or "funicual" in source_lower:
        return _match("floibanen_funicular", "ticket", "Fløibanen Funicular", source_title=source_title)

    if "must-see bergen" in source_lower and ("foot" in source_lower or "boat" in source_lower or "ferry" in source_lower):
        return _match("bergen_foot_and_boat", "walking_boat_tour", "Bergen Walking & Boat Tour", source_title=source_title, variant_tags=("walking", "boat"))

    if "bergen" in source_lower and ("past & present" in source_lower or "past and present" in source_lower or "walk through bergen" in source_lower):
        return _match("bergen_past_present_walk", "walking_tour", "Guided Walking Tour of Bergen Past & Present", source_title=source_title)

    if "mostraumen" in source_lower:
        return _match("mostraumen_fjord_cruise", "fjord_cruise", "Mostraumen Fjord Cruise", source_title=source_title)

    if "geiranger" in source_lower and ("fjord cruise" in source_lower or "cruise day trip" in source_lower or "boat and bus" in source_lower):
        title = "Ålesund-Geiranger Fjord Tour by Boat and Bus" if "one way" in source_lower or "boat and bus" in source_lower else "Geiranger Fjord Cruise Day Trip"
        return _match("geiranger_fjord_cruise", "fjord_cruise", title, source_title=source_title)

    if "ålesund" in source_lower and "hop" in source_lower and "off" in source_lower:
        return _match("alesund_hop_on_hop_off", "ticket", "Ålesund Hop-On Hop-Off 24-Hour Ticket", source_title=source_title)

    if "santa claus" in source_lower and "husky" in source_lower and "reindeer" in source_lower:
        title = "City Highlights, Santa Claus Village & Husky-Reindeer Safari" if "city highlights" in source_lower else "Santa Claus Village, Husky & Reindeer Experience"
        tags = tuple(tag for tag, marker in (("arktikum", "arktikum"), ("lunch", "lunch")) if marker in source_lower)
        return _match("santa_husky_reindeer", "combined_activity", title, source_title=source_title, variant_tags=tags)

    if "santa claus" in source_lower and "reindeer" in source_lower:
        if "husky" in source_lower or "huskies" in source_lower:
            return _match("meet_santa_reindeer_huskies", "combined_activity", "Meet Santa Claus, Reindeer Ride & Greet Huskies", source_title=source_title)
        return _match("santa_village_reindeer", "combined_activity", "Santa Claus Village & Reindeer Visit", source_title=source_title)

    if "korouoma" in source_lower:
        title = "Korouoma Frozen Waterfalls Hike & BBQ" if "frozen" in source_lower or "bbq" in source_lower else "Arctic Korouoma Canyon Wilderness Hike"
        return _match("korouoma_canyon", "hike", title, source_title=source_title)

    if "ranua" in source_lower and "wildlife" in source_lower:
        return _match("ranua_wildlife_park", "wildlife_park", "Arctic Wildlife Adventure to Ranua Park", source_title=source_title)

    if "snowmobile" in source_lower:
        if "evening" in source_lower or "aurora" in source_lower or "northern light" in source_lower:
            return _match("snowmobile_evening_safari", "snowmobile", "Snowmobile Evening Safari & Aurora Opportunity", source_title=source_title)
        return _match("snowmobile_adventure", "snowmobile", source_title if source_title and "snowmobile" in source_title.lower() else "Snowmobile Adventure", source_title=source_title)

    if "icebreaker" in source_lower:
        return _match("arctic_icebreaker_cruise", "icebreaker_cruise", "Arctic Explorer Icebreaker Cruise", source_title=source_title)

    if "crystal lavvo" in source_lower or ("lyngen" in source_lower and "lavvo" in source_lower):
        return _match("lyngen_crystal_lavvo", "overnight_activity", "Lyngen Alps Crystal Lavvo Stay", source_title=source_title)

    if "northern light" in source_lower or "aurora" in source_lower:
        # Avoid renaming daytime activities that merely mention a chance of aurora in notes.
        title_lower = source_title.lower()
        title_has_aurora = "northern light" in title_lower or "aurora" in title_lower
        if title_has_aurora or any(marker in source_lower for marker in ("basecamp", "base camp", "photo chase", "photo tour", "photography", "ice floating", "under the northern lights", "northern lights cruise", "northern lights dinner")):
            return _match("northern_lights_activity", "northern_lights", _northern_lights_title(source_lower, source_title), source_title=source_title)

    if "blue lagoon" in source_lower:
        if "volcano" in source_lower or "fagradalsfjall" in source_lower or "eruption" in source_lower:
            return _match("blue_lagoon_volcano", "guided_day_tour", "Blue Lagoon & Volcano Eruption Site Tour", source_title=source_title)
        return _match("blue_lagoon_admission", "admission", "Blue Lagoon Admission", source_title=source_title)

    if "sky lagoon" in source_lower:
        return _match("sky_lagoon_saman_pass", "admission", "Sky Lagoon Saman Pass & 7-Step Ritual", source_title=source_title)

    if "silfra" in source_lower and ("snork" in source_lower or "drysuit" in source_lower):
        return _match("silfra_drysuit_snorkelling", "snorkelling", "Drysuit Snorkelling in Silfra", source_title=source_title)

    if "whale" in source_lower and ("watching" in source_lower or "marine" in source_lower or "safari" in source_lower):
        if "arctic wildlife" in source_lower or "rib boat" in source_lower or "wildlife safari" in source_lower:
            return _match("arctic_whale_wildlife_safari", "whale_safari", "Whale Watching & Arctic Wildlife Safari", source_title=source_title)
        if "tromsø" in source_lower or "tromso" in source_lower or "arctic cruise" in source_lower:
            return _match("tromso_whale_safari", "whale_safari", "Winter Whale Safari by Arctic Cruise", source_title=source_title)
        if "marine" in source_lower:
            return _match("reykjavik_whale_marine", "marine_cruise", "Whale & Marine Tour", source_title=source_title)
        if "from downtown" in source_lower:
            return _match("reykjavik_whale_watching_downtown", "marine_cruise", "Whale Watching From Downtown", source_title=source_title)
        return _match("whale_watching", "marine_cruise", "Whale Watching", source_title=source_title)

    if "golden circle" in source_lower:
        return _match("golden_circle", "guided_day_tour", source_title if source_title and "golden circle" in source_title.lower() else "Golden Circle Tour", source_title=source_title)

    if "south coast" in source_lower and ("glacier" in source_lower or "black sand" in source_lower):
        title = "South Coast & Glacier Hike Minibus Expedition" if "glacier hike" in source_lower or "hike on" in source_lower else "South Coast, Glacier & Black Sand Beach Tour"
        return _match("iceland_south_coast", "guided_day_tour", title, source_title=source_title)

    if "snæfellsnes" in source_lower or "snaefellsnes" in source_lower:
        return _match("snaefellsnes_peninsula", "guided_day_tour", "Snæfellsnes Peninsula Tour", source_title=source_title)

    if "kvaløya" in source_lower or "sommarøy" in source_lower or "sommaroy" in source_lower:
        if "accessible" in source_lower:
            title = "Accessible Fjord Tour of Kvaløya & Sommarøy"
        elif "photo" in source_lower:
            title = "Photo Tour to Arctic Landscapes and Fjords"
        else:
            title = "Fjord Tour of Kvaløya & Sommarøy"
        return _match("tromso_kvaloya_sommaroy_fjord", "fjord_sightseeing", title, source_title=source_title)

    if ("tromsø" in source_lower or "tromso" in source_lower) and any(marker in source_lower for marker in ("cable car", "round trip ticket", "viewpoint ticket", "fjellheisen")):
        return _match("tromso_cable_car_ticket", "ticket", "Tromsø Cable Car Round-Trip Ticket", source_title=source_title)

    if "reindeer" in source_lower and "sami" in source_lower:
        if "night" in source_lower or "northern light" in source_lower:
            title = "Night Reindeer Sledding & Chance of Northern Lights"
        elif "sledding" in source_lower:
            title = "Short Reindeer Sledding, Reindeer Feeding & Sámi Culture"
        else:
            title = "Reindeer Feeding and Sámi Culture"
        return _match("tromso_reindeer_sami", "sami_reindeer", title, source_title=source_title)

    if "copenhagen" in source_lower and "city walking" in source_lower and "canal" in source_lower:
        return _match("copenhagen_walking_canal", "walking_boat_tour", "Copenhagen Walking & Canal Tour", source_title=source_title)

    if "copenhagen" in source_lower and "canal" in source_lower and "walking" not in source_lower and any(marker in source_lower for marker in ("cruise", "boat", "harbor", "harbour")):
        return _match("copenhagen_canal_cruise", "canal_cruise", source_title if source_title and "canal" in source_title.lower() else "Copenhagen Canal Cruise", source_title=source_title)

    if "tivoli" in source_lower:
        return _match("tivoli_gardens_ticket", "ticket", _ticket_title(source_title, "Tivoli Gardens Entrance Ticket"), source_title=source_title)

    if "stockholm" in source_lower and "vasa" in source_lower and "old town" in source_lower:
        return _match("stockholm_vasa_old_town_boat", "walking_museum_boat_tour", "Stockholm Must-See Tour with Vasa Museum, Old Town & Boat Trip", source_title=source_title)

    if "stockholm" in source_lower and "city highlights" in source_lower and "boat" in source_lower:
        return _match("stockholm_city_highlights_boat", "boat_tour", "Stockholm City Highlights Boat Tour", source_title=source_title)

    if "stockholm" in source_lower and "vasa" in source_lower and any(marker in source_lower for marker in ("ticket", "tickets", "entrance", "entry", "admission", "museum")):
        return _match("vasa_museum_ticket", "admission", _ticket_title(source_title, "Vasa Museum Entrance Ticket"), source_title=source_title)

    if "archipelago" in source_lower and "stockholm" in source_lower:
        return _match("stockholm_archipelago_tour", "boat_tour", "Stockholm Archipelago Tour with Guide", source_title=source_title)

    if "skyview" in source_lower or "sky high views" in source_lower:
        return _match("skyview_stockholm_ticket", "ticket", _ticket_title(source_title, "SkyView Stockholm Ticket"), source_title=source_title)

    if "sigtuna" in source_lower:
        return _match("sigtuna_city_walk", "walking_tour", "Sigtuna City Walk", source_title=source_title)

    if "gothenburg" in source_lower and ("boat ride" in source_lower or "göta river" in source_lower or "goth-river" in source_lower):
        return _match("gothenburg_gota_river_boat", "boat_tour", "Gothenburg Göta River Boat Ride", source_title=source_title)

    if "helsinki" in source_lower and "suomenlinna" in source_lower:
        return _match("helsinki_suomenlinna_day_tour", "city_fortress_tour", "Helsinki City Highlights & Suomenlinna Day Tour", source_title=source_title)

    if "finntastic" in source_lower:
        return _match("finntastic_helsinki_walk", "walking_tour", "A Finntastic Walking Tour in Helsinki", source_title=source_title)

    if "porvoo" in source_lower:
        return _match("helsinki_porvoo_half_day", "guided_half_day_tour", "Porvoo Half-Day Sightseeing Tour", source_title=source_title)

    if "wildlife photography" in source_lower and "longyearbyen" in source_lower:
        return _match("svalbard_wildlife_photography", "wildlife_photography", "Wildlife Photography Around Longyearbyen", source_title=source_title)

    if "wildlife and glacier" in source_lower or "hybrid catamaran" in source_lower:
        return _match("svalbard_wildlife_glacier_catamaran", "wildlife_cruise", "Wildlife & Glacier Hybrid Catamaran Tour", source_title=source_title)

    if "photo tour" in source_lower and "reine" in source_lower and "svolvær" in source_lower:
        return _match("lofoten_photo_tour", "photo_tour", "Photo Tour to Reine, Vestvågøy, Flakstadøy & More", source_title=source_title)

    if "mountain hike" in source_lower and "abisko" in source_lower:
        return _match("abisko_mountain_hike", "hike", "Mountain Hike in Abisko", source_title=source_title)

    return None
