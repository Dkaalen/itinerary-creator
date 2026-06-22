"""Constants and compiled patterns for group-tour package contracts."""

from __future__ import annotations

import re

GROUP_TOUR_CONTRACT_KIND = "group_tour_package"
GROUP_TOUR_CONTRACT_VERSION = 1
GROUP_TOUR_PRODUCT_TYPE = "multi_day_group_tour"
GROUP_TOUR_CANONICAL_FAMILY = "guided_group_tour"

_VALID_SEASONS = frozenset({"summer", "winter", "all", "unknown"})
_GROUP_MASTER_MARKERS = (
    "group tour",
    "holiday package",
    "minibus tour",
    "tour around iceland",
    "guided holiday",
)
_CONDITIONAL_MARKERS = (
    "if weather",
    "weather permitting",
    "depending on",
    "not guaranteed",
    "upon request",
    "subject to availability",
    "subject to weather",
    "subject to road",
    "if snow",
    "when conditions",
    "conditions allow",
)

_PACKAGE_DAY_RE = re.compile(r"^\s*Day\s*(\d+)\s*(?::|\s*-\s*)\s*(.*)$", re.IGNORECASE | re.DOTALL)
_ITINERARY_DAY_RE = re.compile(r"\bDay\s*(\d+)\b", re.IGNORECASE)
_DECLARED_DURATION_RE = re.compile(r"\b(\d+)\s*[- ]\s*day\b", re.IGNORECASE)
_TIME_FIELD_RE = re.compile(
    r"\bTime\s*:\s*(.*?)(?=\s+-\s+(?:(?:Meeting\s*point|Includes|Description|Overview|Note)\s*:|[A-ZÁÉÍÓÚÝÞÆÖ])|$)",
    re.IGNORECASE | re.DOTALL,
)
_MEETING_FIELD_RE = re.compile(
    r"\bMeeting\s*point\s*:\s*(.*?)(?=\s+-\s+(?:Time|Includes|Description|Overview|Note)\s*:|$)",
    re.IGNORECASE | re.DOTALL,
)
_INCLUDES_FIELD_RE = re.compile(r"\bIncludes\s*:\s*(.*)$", re.IGNORECASE | re.DOTALL)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# Route extraction is intentionally conservative.  These are regions and
# settlements used by the supplied Iceland package corpus, not every attraction
# mentioned in daily prose.
_ICELAND_ROUTE_PLACES = (
    "Reykjavík",
    "Reykjavik",
    "West Iceland",
    "Borgarfjörður",
    "Borgarfjordur",
    "Snæfellsnes",
    "Snaefellsnes",
    "Golden Circle",
    "South Coast",
    "Vík",
    "Vik",
    "Skaftafell",
    "Jökulsárlón",
    "Jokulsarlon",
    "Höfn",
    "Hofn",
    "Vatnajökull",
    "Vatnajokull",
    "Eastfjords",
    "East Fjords",
    "Egilsstaðir",
    "Egilsstadir",
    "Mývatn",
    "Myvatn",
    "Akureyri",
    "Hauganes",
    "Borgarnes",
)

_ICELAND_DAY_ATTRACTIONS = (
    "Hvalfjörður",
    "Hvalfjordur",
    "Hraunfossar",
    "Barnafoss",
    "Deildartunguhver",
    "Reykholt",
    "Snæfellsjökull",
    "Snaefellsjokull",
    "Gerðuberg",
    "Gerduberg",
    "Ytri-Tunga",
    "Ytri Tunga",
    "Arnarstapi",
    "Djúpalónssandur",
    "Djupalonssandur",
    "Kirkjufell",
    "Þingvellir",
    "Thingvellir",
    "Geysir",
    "Strokkur",
    "Gullfoss",
    "Bruarfoss",
    "Seljalandsfoss",
    "Gljúfrabúi",
    "Gljufrabui",
    "Skógafoss",
    "Skogafoss",
    "Reynisfjara",
    "Diamond Beach",
    "VÖK Baths",
    "Vok Baths",
    "Dettifoss",
    "Námskarð",
    "Namaskard",
    "Goðafoss",
    "Godafoss",
)


