"""Central text-cleanup rule tables.

This module owns typo, casing and QA text-pattern rules used by parser,
client-polish and real-output QA layers.  It deliberately has no parser,
renderer or Streamlit imports, so product code can share the same rule source
without creating architecture cycles.
"""

from __future__ import annotations

import re
from typing import Iterable

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
    (r"\bcrusie\s+port\b", "Cruise Port"),
    (r"\bcrusie\b", "cruise"),
    (r"\bCrusie\b", "Cruise"),
    (r"\bMeeteing\b", "Meeting"),
    (r"\bFunicluar\b", "Funicular"),
    (r"\bFunicual\b", "Funicular"),

    (r"\bCentraly\b", "Centrally"),
    (r"\bGuest\s+Hose\b", "Guest House"),
    (r"\bFree\s+wifi\b", "Free Wi-Fi"),
    (r"\bfree\s+wifi\b", "Free Wi-Fi"),
    (r"\bActvity\b", "Activity"),
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
    (r"\binlc\b", "incl"),
    (r"\b4Star\b", "4 Star"),
    (r"\b3Star\b", "3 Star"),
    (r"\bHellsinki\b", "Helsinki"),
    (r"\bEngish\b", "English"),
    (r"\bAlesund\b", "Ålesund"),
    (r"\bFlam\b", "Flåm"),
    (r"\bFLam\b", "Flåm"),
    (r"\bSaariselka\b", "Saariselkä"),
]

PROPER_NOUN_REPLACEMENTS = [
    (r"\bsouth\s+coast\b", "South Coast"),
    (r"\bnorth\s+iceland\b", "North Iceland"),
    (r"\beast\s+iceland\b", "East Iceland"),
    (r"\beastfjords\b", "Eastfjords"),
    (r"\bwestfjords\b", "Westfjords"),
    (r"\bwest\s+iceland\b", "West Iceland"),
    (r"\bsn[æa]fellsnes\b", "Snæfellsnes"),
    (r"\bborgarfj[oö]r[dð]ur\b", "Borgarfjörður"),
    (r"\bhallormssta[ðd]ask[oó]gar\b", "Hallormsstaðaskógar"),
    (r"\blagaflj[oó]t\b", "Lagafljót"),
    (r"\bm[yý]vatn\b", "Mývatn"),
    (r"\bn[áa]mskar[ðd]\b", "Námskarð"),
    (r"\bdettifoss\b", "Dettifoss"),
    (r"\bgo[ðd]afoss\b", "Goðafoss"),
    (r"\bhauganes\b", "Hauganes"),
    (r"\bskaftafell\b", "Skaftafell"),
    (r"\bkatla\b", "Katla"),
    (r"\bvatnaj[oö]kull\b", "Vatnajökull"),
    (r"\bj[oö]kuls[áa]rl[oó]n\b", "Jökulsárlón"),
    (r"\bblue\s+ice\s+cave\b", "Blue Ice Cave"),
    (r"\bdiamond\s+beach\b", "Diamond Beach"),
    (r"\bwhale\s+watching\b", "Whale Watching"),
    (r"\bice\s+cave\b", "Ice Cave"),
    (r"\bglacier\s+lagoon\b", "Glacier Lagoon"),
    (r"\bfjellheisen\b", "Fjellheisen"),
]

CASE_REPLACEMENTS = [
    (r"\bHScandic\b", "Scandic"),
    (r"\bMArina\b", "Marina"),
    (r"\bGrand\s+MArina\b", "Grand Marina"),
    (r"\bFunicual\b", "Funicular"),
    (r"\bFunicualr\b", "Funicular"),
    (r"\bComfort\s+hotel\b", "Comfort Hotel"),
    (r"\bquality\s+grand\b", "Quality Grand"),
    (r"\bscandic\b", "Scandic"),
    (r"\bthon\s+hotel\b", "Thon Hotel"),
    (r"\bhotel\s+mayfair\b", "Hotel Mayfair"),
    (r"\bsanta's\s+hotel\b", "Santa's Hotel"),
    (r"\bstandard\s+doubel\s+room\b", "Standard Double Room"),
    (r"\bstandard\s+double\s+room\b", "Standard Double Room"),
    (r"\bstandard\s+room\b", "Standard Room"),
]

SUPPLIER_TYPO_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"\bDate dependant\b", "date-dependent typo leaked", "error"),
    (r"\bFunicual\b", "funicular typo leaked", "error"),
    (r"\bFunicualr\b", "funicular typo leaked", "error"),
    (r"\bProfesional\b", "professional typo leaked", "error"),
    (r"\bFree wifi\b", "WiFi capitalization typo leaked", "error"),
    (r"\baiport\b", "airport typo leaked", "error"),
    (r"\bdoulbe\b", "double typo leaked", "error"),
    (r"\bmilage\b", "mileage typo leaked", "error"),
    (r"\bActvity\b", "activity typo leaked", "error"),
    (r"\bCentraly\b", "centrally typo leaked", "warning"),
    (r"\bGuest Hose\b", "guest house typo leaked", "warning"),
)

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

COMPILED_COMMON_TEXT_REPLACEMENTS = tuple(
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in COMMON_TEXT_REPLACEMENTS
)
COMPILED_CASE_REPLACEMENTS = tuple(
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in (*CASE_REPLACEMENTS, *PROPER_NOUN_REPLACEMENTS)
)
COMPILED_SUPPLIER_TYPO_PATTERNS = tuple(
    (re.compile(pattern, re.IGNORECASE), label, severity)
    for pattern, label, severity in SUPPLIER_TYPO_PATTERNS
)


def apply_regex_replacements(text: str, rules: Iterable[tuple[str, str]] | Iterable[tuple[re.Pattern[str], str]]) -> str:
    """Apply regex replacements while allowing raw or precompiled rules."""

    value = str(text or "")
    for pattern, replacement in rules:
        if hasattr(pattern, "sub"):
            value = pattern.sub(replacement, value)  # type: ignore[union-attr]
        else:
            value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)  # type: ignore[arg-type]
    return value


def apply_common_text_replacements(text: str) -> str:
    """Apply source/supplier typo replacements shared by parser and polish."""

    return apply_regex_replacements(text, COMPILED_COMMON_TEXT_REPLACEMENTS)


def apply_case_replacements(text: str) -> str:
    """Apply client-facing casing and proper-noun replacements."""

    return apply_regex_replacements(text, COMPILED_CASE_REPLACEMENTS)


def iter_supplier_typo_matches(text: str):
    """Yield QA typo matches from the same rule source used by cleanup."""

    value = str(text or "")
    for pattern, label, severity in COMPILED_SUPPLIER_TYPO_PATTERNS:
        match = pattern.search(value)
        if match:
            yield pattern, label, severity, match


__all__ = [
    "CASE_REPLACEMENTS",
    "COMMON_TEXT_REPLACEMENTS",
    "COMPILED_CASE_REPLACEMENTS",
    "COMPILED_COMMON_TEXT_REPLACEMENTS",
    "COMPILED_SUPPLIER_TYPO_PATTERNS",
    "PROPER_NOUN_REPLACEMENTS",
    "SUPPLIER_TYPO_PATTERNS",
    "SUSPICIOUS_FRAGMENTS",
    "apply_case_replacements",
    "apply_common_text_replacements",
    "apply_regex_replacements",
    "iter_supplier_typo_matches",
]
