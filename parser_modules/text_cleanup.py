"""Shared parser text cleanup helpers."""

import re
from functools import lru_cache

import diagnostics
from place_aliases import normalize_place_text
from text_polish import polish_client_text


def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


COMMON_TEXT_REPLACEMENTS = [
    # Multi-word commercial markers first, before individual typo cleanup.
    (r"\bself\s+arrnaged\b", "self-arranged"),
    (r"\bself\s+arrnage\b", "self-arranged"),
    (r"\bself\s+arrange\b", "self-arranged"),
    (r"\bself\s+arranged\b", "self-arranged"),
    (r"\bcost\s+not\s+inclueded\b", "cost not included"),
    (r"\bcost\s+not\s+inclued\b", "cost not included"),
    (r"\bprice\s+not\s+inclueded\b", "price not included"),
    (r"\bprice\s+not\s+inclued\b", "price not included"),
    (r"\bNUtshell\b", "Nutshell"),
    (r"\bNuthsell\b", "Nutshell"),
    (r"\bnuthsell\b", "Nutshell"),
    (r"\bExcurssion\b", "Excursion"),
    (r"\btransfere\b", "transfer"),
    (r"\bTrasnfer\b", "Transfer"),
    (r"\bFlgiht\b", "Flight"),
    (r"\bfeeding\s+the\s+her\b", "feeding the herd"),
    (r"\bcrusie\b", "cruise"),
    (r"\bCrusie\b", "Cruise"),
    (r"\bMeeteing\b", "Meeting"),
    (r"\bFunicluar\b", "Funicular"),
    (r"\bFunicual\b", "Funicular"),
    (r"\bProfesional\b", "Professional"),
    (r"\bathmosphere\b", "atmosphere"),
    (r"\bKristinsand\b", "Kristiansand"),
    (r"\bChocholate\b", "chocolate"),
    (r"\bKvikklunch\b", "Kvikk Lunsj"),
    (r"\bDesctiption\b", "Description"),
    (r"\bKrongborg\b", "Kronborg"),
    (r"\bRosklide\b", "Roskilde"),
    (r"\bSt\s+Nickolas\b", "St Nicholas"),
    (r"\bFLybus\b", "Flybus"),
    (r"\bHlesinkih?\b", "Helsinki"),
    (r"\bHelisnki\b", "Helsinki"),
    (r"\bReyakjvik\b", "Reykjavík"),
    (r"\bReykjavik\b", "Reykjavík"),
    (r"\bFlyBus\b", "Flybus"),
    (r"\bReykajvik\b", "Reykjavík"),
    (r"\bReykavik\b", "Reykjavík"),
    (r"\bCity Centre\b", "city centre"),
    (r"\bKøbenhavn\b", "Copenhagen"),
    (r"\bStaion\b", "Station"),
    (r"\bPirce\b", "price"),
    (r"\bNutsheel\b", "Nutshell"),
    (r"\bNorway\s+in\s+a\s+Nutshell\b", "Norway in a Nutshell"),
    (r"\bBrekafast\b", "Breakfast"),
    (r"\bOverngiht\b", "Overnight"),
    (r"\bBrekfast\b", "Breakfast"),
    (r"\bDoubel\b", "Double"),
    (r"\bArrnaged\b", "arranged"),
    (r"\binclueded\b", "included"),
    (r"\binclued\b", "included"),
    (r"\bBergent\b", "Bergen"),
    (r"\bSvolaver\b", "Svolvær"),
    (r"\bSVolaver\b", "Svolvær"),
    (r"\bSvolvaer\b", "Svolvær"),
    (r"\bSvoalvaer\b", "Svolvær"),
    (r"\bRovaneimi\b", "Rovaniemi"),
    (r"\bTrosmø\b", "Tromsø"),
    (r"\bTrosmo\b", "Tromsø"),
    (r"\bGothernburg\b", "Gothenburg"),
    (r"\bGothenBurg\b", "Gothenburg"),
    (r"\bGothenburg\b", "Gothenburg"),
    (r"\bGothenbrug\b", "Gothenburg"),
    (r"\baccommodaiton\b", "accommodation"),
    (r"\binlcuded\b", "included"),
    (r"\bInlcuded\b", "Included"),
    (r"\bIncludse\b", "Includes"),
    (r"\bFull\s+Pention\b", "Full pension"),
    (r"\bFull\s+Pension\b", "Full pension"),
    (r"\bOptinal\b", "Optional"),
    (r"\bUpgradesd\b", "Upgrades"),
    (r"\bavaiable\b", "available"),
    (r"\bavaialble\b", "available"),
    (r"\bteminal\b", "terminal"),
    (r"\barrivak\b", "arrival"),
    (r"\btickert\b", "ticket"),
    (r"\bPirvate\b", "Private"),
    (r"\bRecepion\b", "Reception"),
    (r"\bStaion\b", "Station"),
    (r"\bKriuna\b", "Kiruna"),
    (r"\bwitj\b", "with"),
    (r"\bTromso\b", "Tromsø"),
    (r"\bTallinnn\b", "Tallinn"),
    (r"\bTallin\b", "Tallinn"),
    (r"\bKakslauttenen\b", "Kakslauttanen"),
    (r"\b(\d{1,2})\s+:\s*(\d{2})", r"\1:\2"),
    (r"\bWi-FI\b", "Wi-Fi"),
    (r"\bPickupo\b", "Pick up"),
    (r"\bOtpions\b", "Options"),
    (r"\bticktes\b", "tickets"),
    (r"\bMelas\s+onboard\b", "Meals onboard"),
    (r"\bCLaus\b", "Claus"),
    (r"\bVIllage\b", "Village"),
    (r"\bAfternon\b", "Afternoon"),
    (r"\badditonal\b", "additional"),
    (r"\bROute\b", "Route"),
    (r"\binlc\b", "incl"),
    (r"\b4Star\b", "4 Star"),
    (r"\b3Star\b", "3 Star"),
]


COMPILED_COMMON_TEXT_REPLACEMENTS = tuple(
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in COMMON_TEXT_REPLACEMENTS
)


SECTION_BOUNDARY_PATTERNS = (
    r"Overview",
    r"What[’']?s included\??",
    r"What to expect\??",
    r"Not Included",
    r"Not included",
    r"Includes?\s*:",
    r"Included\s*:",
    r"Pick[-\s]*up\s*/\s*meeting\s*point",
    r"Pick[-\s]*up\s*:",
    r"Meeting Point\s*:",
    r"Meeting point\s*:",
    r"Highlights?\s*:",
    r"Itinerary",
    r"Packages",
)

RUN_ON_ITEM_STARTS = (
    "Personalized",
    "Harbor ferry",
    "Change of guards",
    "Guided visit",
    "Guided walking",
    "City cruise",
    "English-speaking",
    "Professional",
    "Knowledgeable",
    "Sightseeing",
    "Bottled water",
    "Thermal",
    "Winter",
    "Hot drinks",
    "Hot drink",
    "Snowsuits",
    "Stories about",
    "Feeding",
    "Traditional",
    "Pick-up/drop-off",
    "Pickup/drop-off",
    "Cruise on",
    "Free",
    "Warm",
    "Walking tour",
    "Authorized",
    "Other languages",
    "Towels",
    "Warm drink",
    "Helmet",
    "Wi-Fi",
    "Equipment",
    "Visit to",
    "Visit",
    "Private transfer",
    "Glacier hiking",
    "English &",
    "English and",
    "Round-trip",
)


def repair_supplier_section_boundaries(value: str) -> str:
    """Insert safe boundaries into run-on supplier cells before parsing.

    Supplier exports often paste labels and list items together, e.g.
    ``KøbenhavnOverviewSee...`` or ``guideVisit to...``.  Repairing the
    source once here keeps meeting points, inclusions and descriptions from
    swallowing each other across the parser/generator/PDF stack.
    """

    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return text

    # Label stuck to previous prose: ``KøbenhavnOverview``.
    label_group = "|".join(SECTION_BOUNDARY_PATTERNS)
    text = re.sub(rf"(?<=[A-Za-zÀ-ÿøØåÅäÄöÖ0-9).])(?=(?:{label_group}))", "\n", text, flags=re.IGNORECASE)

    # Label stuck to following prose: ``OverviewSee`` / ``What's included?Pick-up``.
    text = re.sub(r"\b(Overview|What[’']?s included\?|What to expect\?|Not Included|Not included|Itinerary|Packages)(?=[A-ZÀ-ÖØ-Þ])", r"\1\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(Pick[-\s]*up\s*/\s*meeting\s*point|Meeting Point|Meeting point|Highlights?)(\s*:)(?=[A-ZÀ-ÖØ-Þ])", r"\1\2\n", text, flags=re.IGNORECASE)

    # Inclusion/list item stuck to previous item: ``guideVisit to...``.
    item_group = "|".join(re.escape(item) for item in RUN_ON_ITEM_STARTS)
    text = re.sub(rf"(?<=[a-zøåäöéèüñ),])(?=(?:{item_group})(?:\b|\s))", "\n", text)

    # Common no-space sentence/item joins from supplier exports.
    text = re.sub(r"(?<=[.!?])(?=[A-ZÀ-ÖØ-Þ])", " ", text)
    text = re.sub(r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ]+)(What[’']?s included|What to expect|Overview)\b", r"\1\n\2", text, flags=re.IGNORECASE)
    return text

SUSPICIOUS_FRAGMENTS = [
    "brekafast",
    "brekfast",
    "arrnaged",
    "arrnage",
    "avaialble",
    "teminal",
    "inclueded",
    "inclued",
    "doubel",
    "pirce",
    "staion",
    "bergent",
    "svolaver",
    "svoalvaer",
    "nutsheel",
    "nutshel",
    "excurssion",
    "transfere",
    "crusie",
    "chocholate",
    "desctiption",
    "krongborg",
    "rosklide",
    "nickolas",
]


def fix_common_text(value):
    """Silently fix recurring spelling/capitalization issues in pasted itineraries.

    The public wrapper remains permissive for legacy callers that pass values
    other than strings. Only the canonical string pipeline is cached.
    """

    return _fix_common_text_cached(str(value or ""))


@lru_cache(maxsize=8192)
def _fix_common_text_cached(value: str) -> str:
    text = repair_supplier_section_boundaries(value)

    for pattern, replacement in COMPILED_COMMON_TEXT_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    text = normalize_place_text(text)
    text = polish_client_text(text)

    return clean_space(text) if "\n" not in text else text


def check_for_unknown_typos(text, context=""):
    """Warn if known suspicious fragments remain after normal cleanup."""

    lower = str(text or "").lower()

    for fragment in SUSPICIOUS_FRAGMENTS:
        if fragment in lower:
            diagnostics.warn(
                "possible_typo",
                f"Possible uncorrected typo '{fragment}' found after text cleaning" + (f" in {context}" if context else ""),
                raw_value=str(text or "")[:200],
            )
